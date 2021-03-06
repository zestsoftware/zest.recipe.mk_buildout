import os
import subprocess
import logging
import zc.buildout
import re

class MakeBuildout(object):
    _allowed_options = ['recipe',
                        'python',
                        'paster',
                        'template',
                        'buildout_file',
                        'buildout_rename',
                        'paster_commands',
                        'extra_parts',
                        'extra_options',
                        'extra_eggs',
                        'test_runner']

    _base_options = {'python': 'python',
                     'paster': 'paster',
                     'template': 'plone',
                     'buildout_file': 'buildout.cfg',
                     'buildout_rename': 'buildout_base.cfg',
                     'paster_commands': '',
                     'extra_parts': '',
                     'extra_eggs': '',
                     'extra_options': '',
                     'test_runner': 'bin/test'}

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = {}
        self.options.update(self._base_options)
        self.options.update(options)
        self.clean_options()

    @property
    def logger(self):
        return logging.getLogger(self.name)

    def clean_options(self):
        """ Cleans the potential += things.
        Will append the content to the option is existing or
        create a new entry if needed.
        """
        to_delete = []
        exp = re.compile('(\S*)\s*\+')

        for key in self.options.keys():
            match = exp.match(key)
            if match is None:
                continue

            to_delete.append(key)
            base_key = match.groups()[0]
            value = self.options[key]

            if base_key in self.options:
                self.options[base_key] += '\n%s' % value
            else:
                self.options[key] = value

        # We remove the keys as they've been merged.
        for key in to_delete:
            del self.options[key]

    def _check_command_line(self, command, expected):
        """ Checks that 'excepted' is in the output of the command.
        Command must be a list of string (['ls', '-la'] for example for 'ls -la')
        Raises a ValueError if the command is not found or the excepted
        string is not found in the output.
        """
        try:
            output,error = subprocess.Popen(command, stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()
        except OSError:
            self.logger.error('Command "%s" is not valid' % command[0])
            raise ValueError

        if not expected in output:
            self.logger.error('Expected output from "%s" not found' % ' '.join(command))
            self.logger.error('Expected: %s' % expected)
            self.logger.error('Found: %s' % output)
            raise ValueError

    def check_options(self):
        """ Checks that options provided are correct:
        - python must be a python executable
        - same for paster
        - template must be available in paster templates
        - extra_parts must exist in the original buildout. Rewrite it as a list.
        """
        for option, value in self.options.items():
            if option not in self._allowed_options:
                self.logger.warn('option %s is not recognized' % option)
                continue
        
            if option == 'python':
                self._check_command_line(
                    [value, '-h'],
                    'python [option] ... [-c cmd | -m mod | file | -] [arg] ...')
                
            if option == 'paster':
                self._check_command_line(
                    [value],
                    'paster [paster_options] COMMAND [command_options]')

            if option == 'template':
                try:
                    self._check_command_line(
                        [self.options['paster'], 'create', '--list-template'],
                        '  %s:' % value)
                except ValueError:
                    self.logger.error('Template "%s" unknown in paster' % value)
                    raise ValueError       

            if option == 'extra_parts':
                new_parts = []
                for part in value.split('\n'):
                    if not part:
                        # Might happen with the first line.
                        continue
                    
                    if not part in self.buildout.keys():
                        self.logger.error('Part %s does not exist in the buildout.' % part)
                        continue

                    new_parts.append(part)
                self.options['extra_parts'] = new_parts

    def go_to_parts(self):
        os.chdir(self.buildout['buildout']['parts-directory'])

    def go_to_subbuildout(self):
        os.chdir(os.sep.join([self.buildout['buildout']['parts-directory'],
                              self.name]))

    def create_buildout(self):
        """ Runs the paster command to create the buildout.
        """
        self.go_to_parts()
        self.logger.info('Creating new sub buildout')
        self.logger.info('Running %s create -t %s %s' % (
            self.options['paster'],
            self.options['template'],
            self.name))

        paster_input = os.tmpfile()
        paster_input.write(self.options['paster_commands'].replace("''", ""))
        paster_input.seek(0)
        p = subprocess.Popen([self.options['paster'],
                              'create',
                              '-t',
                              self.options['template'],
                              self.name],
                             stdin = paster_input)
        p.wait()
        paster_input.close()

    def developed_eggs(self):
        eggs = []

        if '_mr.developer' in self.buildout.keys():
            sources = self.buildout['buildout']['sources']
            eggs += self.buildout[sources].keys()

        if 'develop' in self.buildout['buildout']:
            # The egg list will look something like that:
            # 'src/my_egg\nsrc/my_other_egg'
            # We first split on '\n' to get the real list, then we only
            # keep the egg name by splitting on 'os.sep'.
            eggs += [egg.split(os.sep)[-1]
                     for egg in self.buildout['buildout']['develop'].split('\n')]

        return [egg for egg in eggs
                if egg not in ['', 'zest.recipe.mk_buildout',
                               'zest.recipe.multi_buildout_test']]

    def replace_dirs(self, value):
        """ Replaces paths to the main buildout by path
        in the sub-buildout.
        """
        sub_path = os.sep.join([self.buildout['buildout']['parts-directory'],
                              self.name])
        main_path = self.buildout['buildout']['directory']

        return value.replace(main_path, sub_path)

    def add_buildout_file(self):
        """ If needed, will change buildout.cfg in buildout_base.cfg.
        Then creates a buildout.cfg extending the 'buildout_file' option (
        or buildout_base.cfg if it was changed previously).
        """
        self.go_to_subbuildout()
        extends = self.options['buildout_file']

        if self.options['buildout_file'] == 'buildout.cfg':
            if not os.path.exists(self.options['buildout_rename']):
                os.rename('buildout.cfg', self.options['buildout_rename'])
            extends = self.options['buildout_rename']

        b = open('buildout.cfg', 'w')
        b.write("[buildout]\n")
        b.write("extends = %s\n" % extends)

        dev_eggs = self.developed_eggs()
        extra_eggs = [x for x in self.options['extra_eggs'].split('\n') if x]
        # We add the eggs at the buildout level, not the instance one.
        if dev_eggs or extra_eggs:
            b.write('eggs+=\n')
            b.write('\n'.join(['   %s' % egg for egg in dev_eggs + extra_eggs]))
            b.write('\n\n')

        if dev_eggs:
            # We tell the eggs are developped from the main buildout, so the
            # sub-buildout will not download the latest egg from Pypi but the development
            # one (the goal is to test them after all....)
            b.write('develop+=\n')
            b.write('\n'.join(['   %s%ssrc%s%s' % (
                self.buildout['buildout']['directory'], os.sep, os.sep, egg)
                               for egg in dev_eggs]))
            b.write('\n\n')

        # We add extra options to the buildout.
        extra_options = {'buildout': []}
        exp = re.compile('\[(.*)\](.*)')
        
        for option in self.options['extra_options'].split('\n'):
            if not option:
                # First line might be blank.
                continue

            match = exp.match(option)
            if match is None:
                extra_options['buildout'].append(option)
            else:
                part, opt = match.groups()
                if not part in extra_options:
                    extra_options[part] = []
                extra_options[part].append(opt)

        b.write('\n'.join(extra_options['buildout']))
        b.write('\n\n')
        del extra_options['buildout']

        # We also add the extra parts.
        if self.options['extra_parts']:
            b.write('parts+=\n')
            b.write('\n'.join(['  %s' % part
                               for part in self.options['extra_parts']]))
            b.write('\n\n')

            for part in self.options['extra_parts']:
                b.write('[%s]\n' % part)
                for key, value in self.buildout[part].items():
                    if '\n' in value:
                        b.write('%s=\n' % key)
                        b.write('\n'.join(['  %s' % self.replace_dirs(x)
                                           for x in value.split('\n')]))
                    elif value:
                        b.write('%s = %s\n' % (key, self.replace_dirs(value)))

                if part in extra_options:
                    b.write('\n')
                    b.write('\n'.join(
                        [self.replace_dirs(value) for value in extra_options[part]]))
                    del extra_options[part]

                b.write('\n\n')

        for part in extra_options:
            b.write('[%s]\n' % part)
            b.write('\n'.join(
                [self.replace_dirs(value) for value in extra_options[part]]))
            b.write('\n\n')

        b.close()

    def run_bootstrap(self):
        """ If bin/buildout does not exist, runs 'python bootstrap.py'
        """
        if os.path.exists(os.sep.join(['bin', 'buildout'])):
            return

        p = subprocess.Popen([self.options['python'], 'bootstrap.py'])
        p.wait()

    def run_buildout(self):
        """ Run the 'bin/buildout command'
        """
        self.go_to_subbuildout()        
        self.run_bootstrap()
        p = subprocess.Popen(['bin/buildout'])
        p.wait()

    def install(self):
        self.check_options()
        self.create_buildout()
        self.add_buildout_file()
        self.run_buildout()
        return []

    def update(self):
        self.check_options()
        self.run_buildout()
