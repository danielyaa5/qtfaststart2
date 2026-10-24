import io
import os
import re

from setuptools import setup

here = os.path.dirname(os.path.abspath(__file__))

# Read the version without importing the package, which isn't on the path
# in isolated builds
with io.open(os.path.join(here, 'qtfaststart2', '__init__.py'),
             encoding='utf-8') as f:
    version = re.search(r'VERSION = "([^"]+)"', f.read()).group(1)

with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='qtfaststart2',
    author='danielyaa5',
    author_email='danyagithub@gmail.com',
    version=version,
    description='Move the moov atom to the front of MP4 and QuickTime files for fast-start web streaming. A pure Python qt-faststart.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/danielyaa5/qtfaststart2',
    project_urls={
        'Source': 'https://github.com/danielyaa5/qtfaststart2',
        'Changelog': 'https://github.com/danielyaa5/qtfaststart2/blob/master/CHANGES.md',
        'Issues': 'https://github.com/danielyaa5/qtfaststart2/issues',
    },
    license='MIT',
    platforms=["any"],
    packages=['qtfaststart2'],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': ['qtfaststart2=qtfaststart2.command:run'],
    },
    keywords='mp4 mov quicktime moov faststart qt-faststart streaming video ffmpeg',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Multimedia :: Video :: Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
