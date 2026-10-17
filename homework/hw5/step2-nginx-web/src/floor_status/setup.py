from setuptools import setup

package_name = 'floor_status'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='黃信惟',
    maintainer_email='nick.h2k6@gmail.com',
    description='Publish current floor for Docker/ROS 2 communication tests',
    license='MIT',
    entry_points={
        'console_scripts': [
            'floor_publisher = floor_status.floor_publisher:main',
        ],
    },
)
