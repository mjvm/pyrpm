from setuptools import setup, find_packages

version = '0.2'

setup(name='pyrpm',
      version=version,
      description="A pure python rpm reader",
      long_description=""" """,
      classifiers=[],
      keywords="",
      author="Mário Morgado",
      author_email="mjvm@caixamagica.pt",
      url="",
      license="GLP",
      package_dir={'': '.'},
      packages=find_packages(where='.', exclude=('tests',)),
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
                        ],
      entry_points="""
      # Add entry points here
      """,
      )
