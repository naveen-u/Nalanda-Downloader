#!/usr/bin/env python3

#-------------------------------------------------------------------------------
# Name:        Nalanda Downloader
# Purpose:     Download course files from BITS Pilani's LMS
# Author:      Naveen Unnikrishnan
# Created:     19/07/2018
#-------------------------------------------------------------------------------

__author__ = 'Naveen Unnikrishnan'
__version__ = 1.0

import requests
from bs4 import BeautifulSoup
import re
import os
from configparser import ConfigParser
import argparse
import logging
from getpass import getpass
import sys
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

_silent = False
_exit_status = 'Status: Completed'

def make_config_file(root_dir = '', username = '', password = '', date_time = 'A long time ago...', status = ''):
	"""
	Creates new config file
	"""
	config = ConfigParser()
	config['dirs'] = {'root_dir': root_dir}
	config['credentials'] = {'username':username, 'password':password}
	config['last'] = {'datetime':date_time, 'status':status}
	with open('.config.ini', 'w') as configfile:
	  config.write(configfile)

def is_downloadable(header):
    """
    Checks whether the url contain a downloadable resource
    """
    content_type = header.get('content-type')
    if 'text' in content_type.lower():
        return False
    if 'html' in content_type.lower():
        return False
    return True

def is_page(url):
	"""
	Checks whether a url points to a content page
	"""
	if 'mod/page/' in url:
		return True
	else:
		return False

def is_folder(url):
	"""
	Checks whether a url points to a folder with resources
	"""
	if 'mod/folder/' in url:
		return True
	else:
		return False

def get_filename_from_cd(cd):
    """
    Get filename from the content-disposition header
    """
    if not cd:
        return None
    fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]

def get_credentials():
	"""
	Gets credentials from user
	"""
	username = input('Enter username: ')
	password = getpass(prompt = 'Enter password: ')
	root_directory = input('Enter directory path to store course data: ')
	return username, password, root_directory

def prints(str):
	"""
	Silent-mod-friendly print function
	"""
	if _silent is False or _silent is None:
		print(str)

def representsInt(s):
	"""
	Check if s is an integer
	"""
	try: 
		int(s)
		return True
	except ValueError:
		return False



if __name__ == '__main__':

	# Setting up command-line arguments
	parser = argparse.ArgumentParser(prog = 'nalanda-downloader', description = "Download course files from BITS Pilani's LMS.")
	parser.add_argument('--silent', '-s', help = "Don't display status messages.", action = 'store_true')
	parser.add_argument('--log', '-l', help = "Display log messages.", action = 'store_true')	
	parser.add_argument('--user', '-u', help = 'Use user-entered credentials instead of reading from the config file.', action = 'store_true')
	parser.add_argument('--reset', '-r', help = 'Reset default user credentials and directory.', action = 'store_true')
	parser.add_argument('--course', '-c', help = 'Download courses for select courses.', action = 'store_true')
	args = parser.parse_args()

	# Get path of config file
	project_dir = os.path.dirname(os.path.abspath(__file__))
	config_path = os.path.join(project_dir, '.config.ini')

	# Create config file if it doesn't exist
	if not os.path.isfile(config_path):
		make_config_file()

	# In reset mode, set config values and exit
	if args.reset is True:
		username, password, root_directory = get_credentials()
		make_config_file(root_dir = root_directory, username = username, password = password)
		sys.exit(0)

	# Make silent mode active
	if args.silent is True:
		_silent = True

	# Enable logging if log mode is active
	if args.log is True:
		logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
		logging.getLogger().setLevel(logging.DEBUG)
		requests_log = logging.getLogger("requests.packages.urllib3")
		requests_log.setLevel(logging.DEBUG)
		requests_log.propagate = True


	# Input credentials if user mode is active
	if args.user is True:
		username, password, root_directory = get_credentials()

	# Otherwise, read config file
	else:
		
		try:
			# Initialize config parser
			conf = ConfigParser()
			conf.read(config_path)

			# Get credentials from config file
			root_directory = conf.get("dirs", "root_dir")
			username = conf.get("credentials", "username")
			password = conf.get("credentials", "password")
			last_date = conf.get("last","datetime")
			status = conf.get("last","status")

			# Check if any field is empty
			if username == '' or password == '' or root_directory == '':
				raise
		
		except:
			# Get credentials from user if exception occurred
			print("Something's wrong with your .config file. We'll have to do this the old fashioned way.")
			username, password, root_directory = get_credentials()
			choice = input('Make these values default? [y/n]: ')
			if choice.lower() in ['y','yes']:
				make_config_file(root_directory, username, password)

	# Create root directory if it doesn't already exist
	if not os.path.isdir(root_directory):
		os.makedirs(root_directory,exist_ok = True)
	
	# Initializing Nalanda url and login data
	url = 'http://nalanda.bits-pilani.ac.in/login/'
	login_data = dict(username = username, password = password)
	
	prints('Connecting to Nalanda as ' + username)
	prints('Resources last updated: '+last_date+' '+status)

	# Start session
	with requests.Session() as session:

		# Setting up request retries
		retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
		session.mount('http://', HTTPAdapter(max_retries=retries))

		try:
			# Send login data
			prints('Contacting Nalanda and sending authentication details...')
			r = session.post(url,data = login_data, timeout=5)
			r.raise_for_status()
			
			# Get main course page
			prints('Getting list of courses...')
			page = session.get('http://nalanda.bits-pilani.ac.in/my/', timeout=5)
			contents = page.text
			
			# Verify the contents
			if "My courses" not in contents:
				prints("Cannot log in to Nalanda!")
				sys.exit(1)
			
			# Get list of courses
			courses = contents.split(">My courses</h2>")[1].split('All courses')[0]
			regex = re.compile('<li(.*?)</li>')
			course_list = regex.findall(courses)
			courses = []
			for course_string in course_list:
				soup = BeautifulSoup(course_string,'lxml')
				a = soup.find('a')
				course_name = a.text
				course_link = a.get('href')
				courses.append([course_name, course_link])
			
			# Check if in course mode
			if args.course is True:
				print('Courses found: ')
				j = 1
				for i in courses:
					print('\t'+str(j)+') ' + i[0])
					j += 1				

				# Get user's choice for courses
				choices = str(input('Courses to be downloaded (1-'+str(len(courses))+'): '))
				# Parse user's entry
				choices = re.split(r"[^-0-9]", choices)
				choices = list(filter(None, choices))
				result = []
				for part in choices:
					try:
						if '-' in part:
							a, b = part.split('-')
							if representsInt(a) and representsInt(b):
								a, b = int(a), int(b)
								result.extend(range(a, b + 1))
							elif representsInt(a):
								a = int(a)
								result.append(a)
							elif representsInt(b):
								b = int(b)
								result.append(b)
						else:
							a = int(part)
							result.append(a)
					except:
						prints('Oops! Something went wrong when processing '+ str(part) +'.')
				choices = result
			else:
				# If not in course mode, select all courses
				choices = range(1,len(courses)+1)
				prints('Courses found: ')
				j = 1
				for i in courses:
					prints('\t'+str(j)+') ' + i[0])
					j += 1


			# Check for new downloadable content in each course
			for i in choices:

				# Check validity of index
				if i < 1 or i > len(courses):
					prints(str(i) + ' is not a valid index for a course. Skipping this one...')
					continue
				course = courses[i-1]

				# Get directory path for the course
				prints('\nChecking for new '+course[0]+' resources. Please wait...')
				course_name = course[0].replace('/', '_')
				dir_path = os.path.join(root_directory,course_name)
			
				# Create directory for course if it doesn't already exist
				if not os.path.isdir(dir_path):
					os.mkdir(dir_path)

				# Get the Nalanda course page
				page = session.get(course[1], timeout=5)
				contents = page.text

				# Find all sections
				sections = contents.split('<ul class="topics">')[1].split('<aside id="block-region-side-pre"')[0]
				regex = re.compile('<li id="section-.*?</ul></div></li>')
				section_list = regex.findall(sections)

				for section in section_list:
					
					# Get section name and path of section folder
					soup = BeautifulSoup(section,'lxml')
					a = soup.find('li')
					section_name = a.get('aria-label')
					section_name = section_name.replace('/', '_')
					# Combine all "Lecture" or "Topic" sections
					if 'Lecture' in section_name or 'Topic' in section_name:
						section_name = 'Lectures'
					section_path = os.path.join(dir_path,section_name)

					# Extract links in the section
					link_list = [link.get('href') for link in soup.findAll('a', attrs={'href': re.compile("^http://")})]
					
					index = 0
					while index < len(link_list):
						
						# Get link of file/page/folder
						file_url = link_list[index]
						index += 1
						
						# Get headers of link
						r = session.head(file_url, allow_redirects=True)

						# Check if link leads to downloadable content
						if is_downloadable(r.headers):
						
							# Create a folder for the section if it does not already exist
							if not os.path.isdir(section_path):
								os.mkdir(section_path)
						
							# Get filename and path of downloadable file
							filename = get_filename_from_cd(r.headers.get('content-disposition'))
							file_path = os.path.join(section_path,filename)
							
							# Check if file already exists
							if not os.path.isfile(file_path):
								# Download file
								prints('\tDownloading '+filename+'...')
								r = session.get(file_url, allow_redirects=True, timeout=5)
								open(file_path, 'wb').write(r.content)

						# Check if link is that of a content page
						elif is_page(file_url):
							# Get content page
							r = session.get(file_url,allow_redirects=True, timeout=5)
							content = r.text
							content = content.split('<div id="region-main-box"')[1].split('aside id="block-region-side-pre"')[0]
							soup = BeautifulSoup(content,'lxml')
							a = soup.find('section')
							# Get title of page
							filename = soup.find('h2')
							filename = filename.text
							filename = filename.replace('/', '_')
							filename = filename+'.txt'
							file_path = os.path.join(section_path,filename)

							# Create a folder for the section if it does not already exist
							if not os.path.isdir(section_path):
								os.mkdir(section_path)
							
							# Check if file already exists
							if not os.path.isfile(file_path):							
								# Download file
								prints('\tDownloading '+filename+'...')
								# Save the Nalanda page as a text file
								open(file_path, 'w').write(soup.get_text())

						# Check if link is that of a folder
						elif is_folder(file_url):
							# Get folder page
							r = session.get(file_url,allow_redirects=True, timeout=5)
							contents = r.text
							contents = contents.split('<div role="main"')[1].split('<aside id="block-region-side-pre"')[0]
							soup = BeautifulSoup(contents,'lxml')
							# Extract links of files from the page and append to list
							flist = [link.get('href') for link in soup.findAll('a', attrs={'href': re.compile("^http://")})]
							link_list = link_list+flist

		# Catch an interrupt
		except(KeyboardInterrupt, SystemExit):
			print('\nClosing session and quitting...')
			_exit_status = "Status: Interrupted"
			_silent = True

		# Catch other random exceptions
		except Exception as e:
			print('Oops! Looks like something went wrong somewhere.')
			_exit_status = "Status: Error"
			_silent = True

	# Save date, time, and status in .config
	now = datetime.now()
	make_config_file(root_directory, username, password, date_time = now.strftime("%Y-%m-%d %H:%M"), status = _exit_status)
	prints('Finished updating your resources!')