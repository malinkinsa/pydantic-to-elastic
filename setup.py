from setuptools import setup


def readme():
    with open('README.md', 'r') as infile:
        return infile.read()


classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
]

install_requires = [
    'pydantic>=2.0'
]

setup(
    name='pydantic-to-elastic',
    version='0.0.4',
    description='A simple CLI utility for converting Pydantic models to Elasticsearch mappings',
    license='MIT',
    long_description=readme(),
    long_description_content_type='text/markdown',
    keywords='pydantic elasticsearch mappings es, elastic',
    author='Sergey Malinkin',
    author_email='malinkinsa@gmail.com',
    url='https://github.com/malinkinsa/pydantic-to-elastic',
    install_requires=install_requires,
    entry_points={'console_scripts': ['pydantic2es = pydantic2es.main:main']},
    classifiers=classifiers,
)