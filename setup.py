try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import io
import os

import qtfaststart2

# PyPI shows the README as the project description.
with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'README.md'), encoding='utf-8') as readme:
    long_description = readme.read()

setup_params = dict(
    name='qtfaststart2',
    author='danielyaa5',
    author_email='danyagithub@gmail.com',
    version=qtfaststart2.VERSION,
    description='Move the moov atom to the front of MP4 and QuickTime files for fast-start web streaming. A pure Python qt-faststart.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='mp4 mov quicktime faststart qt-faststart moov streaming video ffmpeg',
    url='https://github.com/danielyaa5/qtfaststart2',
    project_urls={
        'Source': 'https://github.com/danielyaa5/qtfaststart2',
        'Issues': 'https://github.com/danielyaa5/qtfaststart2/issues',
        'Changelog': 'https://github.com/danielyaa5/qtfaststart2/blob/master/CHANGES.md',
    },
    download_url = 'https://github.com/danielyaa5/qtfaststart2/archive/{version}.tar.gz'.format(version=qtfaststart2.VERSION),
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
