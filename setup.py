from setuptools import setup

setup(
  name = 'glacierbackup',
  description = 'A tool to track small files and back them up into Glacier enabling disaster-recovery document backups at virtually no cost',
  packages = ['glacierbackup'],
  version = '0.1.0',
  author = 'Aleksander Tuzik',
  author_email = 'aleksander.tuzik@gmail.com',
  url          = 'https://github.com/arkhebuz/GlacierBackup', 
  license='MIT',
  keywords = ['amazon', 'glacier', 'backup', 'aws'],
  classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Programming Language :: Python :: 3',
      'Topic :: System :: Archiving :: Backup',
      'License :: OSI Approved :: MIT License',
  ],
  install_requires=[
      'pycryptodome >= 3.4.6', 
      'boto3 >= 1.4.4'
  ],
  entry_points={
      'console_scripts': [
          'glacierbackup = glacierbackup.command:main'
      ]
  }
)
