from setuptools import setup

setup(
    name='insta-bot',
    version='0.0.0',
    description='An Instagram Bot that follows users that could follow your account and unfollows who doesn\'t follows you.',
    packages=[
        'insta_bot',
    ],
    install_requires=[
        'requests~=2.24.0',
    ],
)
