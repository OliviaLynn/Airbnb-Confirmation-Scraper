# -*- coding: utf-8 -*-

from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import pyzmail, base64
import sys, datetime
from bs4 import BeautifulSoup

"""
TODO:
test on more than just that single sample email
get the data sent to our db
get it up and running on its own, execute every minute or so
"""

# ------------------------------------------------------------------------------
# THE GMAIL EMAIL SCRAPER

# Scrapes emails from a Gmail account using the Gmail API
#   |
#   v
# Decodes and parses these base64 MIME formatted emails using base64 and pyzmail
#   |
#   v
# Parses the HTML this returns using beautiful soup 4

# This code has been extended from Google's starter code at:
#       https://developers.google.com/gmail/api/quickstart/python
#  ---> Make sure you run through their first 2 setup steps before proceeding!
# ------------------------------------------------------------------------------

# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pyzmail36

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('admin_token.pickle'):
        with open('admin_token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'admin_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('admin_token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API
    print("PARSING EMAIL: ", end='')
    results = service.users().messages().list(
        userId='me', q='subject:"reservation confirmed" is:read').execute()
    messages = results.get('messages', [])

    # Grab the first message, if it exists
    if len(messages) > 0:
        message = messages[0]
        rawContent = service.users().messages().get(
            userId='me', id=message['id'], format='raw').execute()
        asciiContent = base64.urlsafe_b64decode(
            rawContent['raw'].encode('ASCII'))

        # Parse MIME formatted message
        try:
            msg = pyzmail.PyzMessage.factory(asciiContent)
            print(msg.get_subject())
            print()
            if msg.html_part != None:
                htmlPart = msg.html_part.get_payload()
                #print(htmlPart[:500], "...\n")
                
                # Save file
                """
                try:
                    with open('temp.html', 'wb') as fout:
                        fout.write(msg.html_part.get_payload())
                    print("Saved file!\n")
                except:
                    print("Could not write file.")
                """
                
                # Parse HTML
                try:
                    soup = BeautifulSoup(htmlPart.decode('utf-8'),'html.parser')
                    parseSoup(msg, soup)
                        
                except:
                    print("BS4 conversion failed, error:", sys.exc_info()[0])
        except:
            print("Pyzmail parse failed, error:",  sys.exc_info()[0])

# ------------------------------------------------------------------------------
# ---------------------------------------------------------------------- PARSING

def parseSoup(msg, soup):
    # Toggle print statements
    #   Parsers are prone to breaking as the UI/structure of the data they parse 
    #   gets changed over time, so keeping this True helps us keep an eye out
    VERBOSE = True
    
    # Parses the beautiful soup object
    tables = soup.find_all("table")

    # PRINTING
    """
    printTableSummary(tables)
    
    printSingleTable("CUSTOMER HOMETOWN", tables[5])
    printSingleTable("CUSTOMER MESSAGE", tables[6])
    printSingleTable("ROOM NAME", tables[9])
    printSingleTable("CHECKIN/OUTS", tables[11], True)
    printSingleTable("NUMBER GUESTS", tables[13])
    printSingleTable("CONFIRMATION CODE", tables[17])
    printSingleTable("TOTAL PRICE", tables[23])
    """

    # PARSING
    customerName = parseCustomerName(msg)
    if VERBOSE: print("[Customer Name]", customerName)

    customerHometown = parseCustomerHometown(tables)
    if VERBOSE: print("[Customer Hometown]", customerHometown)

    customerMessage = parseCustomerMessage(tables)
    if VERBOSE: print("[Customer Message]", customerMessage)

    roomName = parseRoomName(tables)
    if VERBOSE: print("[Room Name]", roomName)

    (checkInStart, checkInEnd, checkInDate, checkOut, checkOutDate) = \
                   parseCheckInAndOut(tables)
    if VERBOSE: print("[CheckIn Date]", checkInDate.date())
    if VERBOSE: print("[Checkin Time]", checkInStart, "-", checkInEnd)
    if VERBOSE: print("[CheckOut Date]", checkOutDate.date())
    if VERBOSE: print("[CheckOut Time]", checkOut)

    numberGuests = parseNumberGuests(tables)
    if VERBOSE: print("[Num Guests]", numberGuests)

    confirmationCode = parseConfirmationCode(tables)
    if VERBOSE: print("[Confirmation]", confirmationCode)

    rawPrice = parseRawPrice(tables)
    if VERBOSE: print("[Raw Price]", rawPrice)
    
    serviceFee = parseServiceFee(tables)
    if VERBOSE: print("[Service Fee]", serviceFee)
    
    totalPrice = parseTotalPrice(tables)
    if VERBOSE: print("[Total Price]", totalPrice)
    
    occupancyTaxes = parseOccupancyTaxes(tables)
    if VERBOSE: print("[Occupancy Taxes]", occupancyTaxes)
    

def parseCustomerName(msg):
    customerName = "---"
    try:
        subject = msg.get_subject()
        subjectArrivalMessage = subject.split('-')[1]
        nameWithWhitespace = subjectArrivalMessage.split("arrives")[0]
        customerName = nameWithWhitespace.strip()
    except:
        print("Error: could not parse customer name")
    return customerName

def parseCustomerHometown(tables):
    customerHometown = "---"
    try:
        cHometownSection = list(tables[5].find_all("th"))[1]
        cHometownParagraph = list(cHometownSection.find_all("p"))[1]
        customerHometown= cHometownParagraph.string.strip()
    except:
        print("Error: could not parse customer hometown")
    return customerHometown

def parseCustomerMessage(tables):
    customerMessage = "---"
    try:
        cMessageSection = list(tables[6].find_all("th"))[0]
        cMessageParagraph = list(cMessageSection.find_all("p"))[0]
        customerMessage = cMessageParagraph.string.strip()
    except:
        print("Error: could not parse customer message")
    return '\"' + customerMessage + '\"'
    
def parseRoomName(tables):
    roomName = "---"
    try:
        roomInformation = tables[9].find("th")
        roomName = roomInformation.find('p').string.strip()[:-1]
    except:
        print("Error: could not parse room name")
    return roomName

def parseCheckInAndOut(tables):
    timeInStart = "---"
    timeInEnd = "---"
    timeOut = "---"
    inDateObj = None
    outDateObj = None
    try:
        # Get a list of the text in our <p> tags
        thList = list(tables[11].find_all("th"))
        checkinList = list(thList[0].stripped_strings)
        checkoutList = list(thList[2].stripped_strings)
        
        # Check-in parse
        inDate = stripNonAscii(checkinList[1])
        inTime = stripNonAscii(checkinList[2])
        inDateObj = datetime.datetime.strptime(inDate, '%b %d, %Y')
        timeRange = inTime.split("in")[1]
        timeRangeSplit = timeRange.split("-")
        timeInStart = timeRangeSplit[0].strip()
        timeInEnd = timeRangeSplit[1].strip()
        
        # Check-out parse
        outDate = stripNonAscii(checkoutList[1])
        outTime = stripNonAscii(checkoutList[2])
        outDateObj = datetime.datetime.strptime(outDate, '%b %d, %Y')
        timeOut = outTime.split("out")[1].strip()
    except:
        print("Error: could not parse check in/out times")
    return (timeInStart, timeInEnd, inDateObj, timeOut, outDateObj)

def parseNumberGuests(tables):
    numberGuests = "---"
    try:
        numGuestsSection = list(tables[13].find_all("th"))[0]
        numberGuests = numGuestsSection.find_all("p")[1].string.strip()
    except:
        print("Error: could not parse number of guests")
    return numberGuests

def parseConfirmationCode(tables):
    confirmationCode = "---"
    try:
        confirmationSection = list(tables[17].find_all("th"))[0]
        confirmationCodeParagraph = list(confirmationSection.find_all("p"))[1]
        confirmationCode = confirmationCodeParagraph.string.strip()
    except:
        print("Error: could not parse confirmation code")
    return confirmationCode

def parseRawPrice(tables):
    rawPrice = "---"
    try:
        rawPriceSection = list(tables[20].find_all("th"))[1]
        rawPrice = rawPriceSection.find("p").string.strip()
    except:
        print("Error: could not parse raw price")
    return rawPrice


def parseServiceFee(tables):
    serviceFee = "---"
    try:
        serviceFeeSection =  list(tables[21].find_all("th"))[1]
        serviceFee = serviceFeeSection.find("p").string.strip()
    except:
        print("Error: could not parse service fee")
    return serviceFee

def parseTotalPrice(tables):
    totalPrice = "---"
    try:
        totalPriceSection = list(tables[23].find_all("th"))[1]
        totalPrice = totalPriceSection.find("p").string.strip()
    except:
        print("Error: could not parse total price")
    return totalPrice

def parseOccupancyTaxes(tables):
    occupancyTaxes = "---"
    try:
        occupancyTaxesSection = list(tables[25].find_all("th"))[0]
        occupancyTaxesPara = occupancyTaxesSection.find("p").string.strip()
        occupancyTaxes = "$" + occupancyTaxesPara.split("$")[1].split(" ")[0]
    except:
        print("Error: could not parse occupancy taxes")
    return occupancyTaxes

# ------------------------------------------------------------------------------
# --------------------------------------------------------- PRINTING / DEBUGGING

def stripNonAscii(s):
    return "".join(c for c in s if ord(c)<128)

def printASCII(s):
    #print("".join(c if ord(c)<128 else '?' for c in s))
    print("".join(c for c in s if ord(c)<128))

def printTableSummary(tables):
    # Prints a summary of the tables that make up our email
    # A helpful human-readable representation of the data we're after
    # Keeping this around so we can fix things in the future if they
    #   change the way they structure their emails
    for i in range(len(tables)):
        if i > 1:
            table = tables[i]
            print("\n------------ TABLE " + str(i))
            for th in table.find_all("th"):
                for item in th.stripped_strings:
                    # Discard non-ASCII chars
                    if i == 11:
                        printASCII(item)
                    else:
                        print(item)

def printSingleTable(title, table, hasNonASCII=False):
    # Also helpful for looking at the html we've scraped
    # The email body is made up of a bunch of <table> tags,
    #   and this will print the html of the <table> tag we specify
    print("------", title, "-"*(20-len(title)))
    for th in table.find_all("th"):
        for item in th.stripped_strings:
            # Discard non-ASCII chars
            if hasNonASCII:
                printASCII(item)
            else:
                print(repr(item))
    print()

# ------------------------------------------------------------------------------
# ---------------------------------------------------------------------- RUNNING

if __name__ == '__main__':
    main()








        

