# -*- coding: utf-8 -*-
"""
This module contains the tool of zest.recipe.mk_buildout
"""
import os
from setuptools import setup, find_packages



version = open(os.path.join("zest", "recipe", "mk_buildout",
                            "version.txt")).read().strip()

long_description=open("README.rst").read() + "\n" + \
                  open(os.path.join("zest", "recipe", "mk_buildout",
                                    "HISTORY.txt")).read()

entry_points = {'zc.buildout': ['default = zest.recipe.mk_buildout.mk_buildout:MakeBuildout']}
tests_require = ['zope.testing', 'zc.buildout']

setup(name='zest.recipe.mk_buildout',
      version=version,
      description="Recipe to make a sub-buildout",
      long_description=long_description,
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        'Framework :: Buildout',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: Zope Public License',
        ],
      keywords='',
      author='Vincent Pretre',
      author_email='v.pretre@zestsoftware.nl',
      url='https://github.com/zestsoftware/zest.recipe.mk_buildout/',
      license='ZPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['zest', 'zest.recipe'],
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
                        'zc.buildout'
                        # -*- Extra requirements: -*-
                        ],
      tests_require=tests_require,
      extras_require=dict(tests=tests_require),
      test_suite='zest.recipe.mk_buildout.tests.test_docs.test_suite',
      entry_points=entry_points,
      )
