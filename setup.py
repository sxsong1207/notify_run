from setuptools import setup

setup(
    name='notify_run',
    author="Shuang Song",
    author_email="sxsong1207@gmail.com",
    version='0.1.1',
    py_modules=['notify_run'],
    install_requires=[
        # Add your project dependencies here
        'configparser',
        'py7zr'
    ],
    entry_points={
        'console_scripts': [
            'notifyrun=notify_run:main',
        ],
    },
)