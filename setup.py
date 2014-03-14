from distutils.core import setup

setup(
    name='MVim',
    version='0.1.0',
    author='Élie Bouttier',
    author_email='elie+mvim@bouttier.eu.org',
    packages=['mvim'],
    scripts=['bin/mvim'],
    url='http://cgit.bouttier.eu.org/mvim/',
    license='LICENSE.rst',
    description='Rename or move files by editing their names with vim.',
    long_description=open('README.rst').read(),
)
