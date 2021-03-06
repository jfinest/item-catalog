# README

## Overview:
Ever read a book that you found interesting enough that you would like to recommend to others? Well, this web application lets you do just that. If you are someone whom just read a book and want to recommen it then simply log in and add the book to the list. Vice versa if you are someone whom is looking for a book to read that others recommend then this is a good place to do so.

## Content:

When project is downloaded following is included:
1. Item-cataglog(folder)
    1.books.db
    2.client_secrets.json
    3.database_setup2.py
    4.project2.py
    5.README.md
    6.static(folder)
        1.style.css
        2.books.jpeg
        3.book.png
        4.books2.jpeg
        5.books3.jpeg
        6.images.jpeg
    7.templates(folder)
        1.booklist.html
        2.bookview.html
        3.categorylist.html
        4.deletebook.html
        5.login.html
        6.main.html
        7.newbook.html
        8.publicbooklist.html
        9.publicbookview.html
        10.publiccategorylist.html


## Requirements:
1. Python (Preferably version 2.7)
2. Flask ()
3. Web Browser of choice

## Install
1. **If using Mac:**
    1. First check if python is installed (preferably python 2.7). From terminal run
        * python -V
    2. If python not found then follow link [here](https://www.python.org/downloads/) to install
    3. Once you have verified python is installed run following command in terminal to install Flask
        * pip install flask
    

2. **If using Windows**
    1. First verify if python is installed in your system by running following command from the command prompt window
        * python
    2. if python is not install then [click here](https://www.python.org/downloads/windows/) to start installation.
    3. After verifying python is installed run folllowing command from the command prompt window:
        * pip install flask

##Downloads
To download file to run web application
    * https://github.com/jfinest/item-catalog
1. If you have access to github simply run
    * git clone https://github.com/jfinest/item-catalog
2. If you dont have git installed then simply click on the **clone or download** button, to download the web applications files.

## Usage
While running web applications to avoid any issues with logging out due to Flask cookie becoming slate, there are two options:
1. By making sure to delete cookie from the site while in regular browsing mode
2. Go into incognito mode since there will be no cookie/cahce.

## Run
1. From Terminal(Mac) or Command Prompt(Windows), need to go to change directory to where the files are located.
2. In order to view info from database we need to run following command:
    **python database_setup2.py**
    This will create the database locally
3. Now by run
    **python books.db**
    This will import all info from the database to your machine locally
4. Then run **python project2.py**
    By running above command, this will start your server locally
5. Lastly, from web browser simply go to the following url which is where your local server is running your web application from. In this case is 
    * localhost:5000/
