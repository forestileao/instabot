from setuptools import setup

setup(
    name='insta-bot',
    version='1.0.0',
    description='An Instagram Bot that follows the followers from a user-target that you choose and unfollows who doesn\'t follows you.',
    packages=[
        'insta_bot',
    ],
    install_requires=[
        'requests~=2.24.0',
    ],
)
