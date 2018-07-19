# Nalanda Downloader

Script to download course files from Nalanda, BITS Pilani's LMS.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Python 3.x

Packages as given in [requirements.txt](requirements.txt)


### Installation

Install the `Requests` and the `Beautiful Soup` packages for python3.

```
pip3 install -r requirements.txt
```

## Usage

- Run `./nalanda-downloader.py`.
- Enter username and password on prompt.
- Enter directory path to store course files.
- Choose whether to make the user-login details default. Enter `y` to set as default. If set, credentials do not have to be entered again in the future.
- List of courses will be printed and downloads will begin. All downloadable files (including files within folders) will be downloaded. Web pages with resources, notices etc. will be downloaded as `.txt` files.
- The directory structure is intuitive. Notices will be downloaded to `Root folder > Course > Notice Section`, lecture slides to `Root folder > Course > Lectures` and so on.
- Use the `--course` or `-c` option to download files for specific courses.
- Use the `--silent` or `-s` option to disable status messages.
- Use the `--reset` or `-r` option to reset stored credentials and exit.
- Use the `--user` or `-u` option to bypass the stored credentials and enter credentials manually.
- Use the ``--log`` or `-l` option to view log messages.

## Authors

* **Naveen Unnikrishnan** - *Initial work* - [naveen-u](https://github.com/naveen-u)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

