import os
import subprocess

import logging
import zc.buildout

class MakeBuildout(object):
    _allowed_options = ['recipe',
                        'python', 'paster',
                        'template', 'buildout_file']
    _base_options = {'python': 'python',
                     'paster': 'paster',
                     'template': 'plone',
                     'buildout_file': 'buildout.cfg'}

    def __init__(self, buildout, name, options):
        self.buildout = buildout
        self.name = name
        self.options = {}
        self.options.update(self._base_options)
        self.options.update(options)

        #install_dir = self.buildout['buildout']['directory']

    @property
    def logger(self):
        return logging.getLogger(self.name)

    def _check_command_line(self, command, expected):
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
        for option, value in self.options.items():
            if option not in self._allowed_options:
                self.logger.info('option %s is not recognized' % option)
                continue
        
            if option == 'python':
                self._check_command_line(
                    [value, '--help'],
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


    def install(self):
        self.logger.info('w00t, installing')
        self.check_options()
        return []

    def update(self):
        self.logger.info('w00t, updating')
        self.check_options()

