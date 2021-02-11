try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import qtfaststart2

setup_params = dict(
    name='qtfaststart2',
    author='danielyaa5',
    author_email='danyagithub@gmail.com',
    version=qtfaststart2.VERSION,
    description='Quicktime atom positioning in Python for fast streaming.',
    url='https://github.com/danielyaa5/qtfaststart2',
    download_url = 'https://github.com/danielyaa5/qtfaststart2/archive/2.0.0.tar.gz',
    license='MIT License',
    platforms=["any"],
    provides=['qtfaststart2'],
    packages=[
        'qtfaststart2',
    ],
    scripts=['bin/qtfaststart2'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)

if __name__ == '__main__':
    setup(**setup_params)
