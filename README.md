# Airbnb Confirmation Email Reader
<img src="https://img.shields.io/badge/python-3.7-blue" /> <img src="https://img.shields.io/badge/selenium-1.141.0-blue" /> <img src="https://img.shields.io/badge/maintained%3F-no-red" /> <img src="https://img.shields.io/github/issues/OliviaLynn/Airbnb-Confirmation-Scraper" />

Scrapes Airbnb confirmation emails from a designated Gmail account.

## Getting Started

These instructions will get the project up and running on your own machine with your own Gmail account.

### Prerequisites

#### Gmail API
- Follow Step 1 of Google's instructions found [here](https://developers.google.com/gmail/api/quickstart/python) to enable the Gmail API and receive the file `credentials.json`, which you should place in the same directory as the scraper
- Install the Google Client Library:
```shell
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```
#### Python Packages
```shell
pip install pyzmail36 beautifulsoup4 pytz
```
- **PyzMail (1.0.4):** Helps us parse the MIME encoding of the emails we scrape. *(using pyzmail36 instead of pyzmail for Python 3.6+!)*
- **Beautiful Soup (4.7.1):** For navigating the html of the email bodies.
- **PyTz (2019.1):** Lets us use timezones.


### Running
- From your shell, run the command:
```shell
$ python OngoingEmailScraper.py <smartbnb-username> <smartbnb-password>
```
- The single pass email scraper has been included for posterity's sake only - you should still be able to run it, but development will only occur on the ongoing scraper.
- Each run will write or update a file `dateOfLastScrape.txt`, which we use when determining if any *new* emails have arrived since our last scrape.
