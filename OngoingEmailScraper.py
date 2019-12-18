# -*- coding: utf-8 -*-

from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import pyzmail, base64
import sys, datetime, json, pytz, time
from bs4 import BeautifulSoup

"""
TODO:
get the data sent to our db
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
    # Get the date and time of the last time we ran the scraper
    dateOfLastScrape = getDateOfLastScrape()
    dateOfLastScrape = dateOfLastScrape.replace(day=7)

    # Grab and parse emails that have arrived since that date and time
    dateAsSeconds = getDateAsSeconds(dateOfLastScrape)
    newMessagesFound = scrapeMessagesAfterDate(dateAsSeconds, dateOfLastScrape)

    # Record what time we ran this, if we did find any new messages
    if newMessagesFound:
        setDateOfLastScrape()

def scrapeMessagesAfterDate(targetDate, targetDateObj):
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
    queries = 'subject:"reservation confirmed" after:{:d}'.format(targetDate)
    results = service.users().messages().list(
        userId='me', q=queries).execute()
        # We can optionally add "is:read" to q to only grab read emails,
        # but for our current use we don't need this
    messages = results.get('messages', [])

    # Initialize our data object
    dataOut = {"messages": []}

    # Grab the first message, if it exists
    if len(messages) > 0:
        print(str(len(messages)) + " messages found.\n")
        for message in messages:
            rawContent = service.users().messages().get(
                userId='me', id=message['id'], format='raw').execute()
            asciiContent = base64.urlsafe_b64decode(
                rawContent['raw'].encode('ASCII'))

            # Parse MIME formatted message
            try:
                msg = pyzmail.PyzMessage.factory(asciiContent)
                print(msg.get_subject())
                msgDate = msg.get_decoded_header("Date")
                print(msgDate)
                parsedDate = datetime.datetime.strptime(msgDate, "%a, %d %b %Y %H:%M:%S %z (%Z)")
                parsedDateAsSeconds = getDateAsSeconds(parsedDate)
                print("{:d} <\n{:d}".format(parsedDateAsSeconds, targetDate))
                print(parsedDateAsSeconds < targetDate)
                print()
                if msg.html_part != None:
                    htmlPart = msg.html_part.get_payload()
                    #print(htmlPart[:500], "...\n")
                    
                    # Parse HTML
                    try:
                        soup = BeautifulSoup(htmlPart.decode('utf-8'),'html.parser')
                        messageJson = parseSoup(msg, soup)
                        dataOut["messages"].append(messageJson)
                            
                    except:
                        print("BS4 conversion failed, error:", sys.exc_info()[0])
            except:
                print("Pyzmail parse failed, error:",  sys.exc_info()[0])
    else:
        print("No new messages received since {:s} UTC".format(targetDateObj.strftime("%m/%d/%y %H:%M:%S")))
        return False
    
    # Save the data we've scraped:
    fileOutName = "emailsSince_{:d}.json".format(targetDate)
    with open(fileOutName, 'w') as outfile:
        json.dump(dataOut, outfile)
    print("Saved JSON as " + fileOutName)
    
    return True
    
# ------------------------------------------------------------------------------
# ------------------------------------------------------ GETTING/RECORDING DATES

def getDateAsSeconds(date):
    utcEpoch = pytz.utc.localize(datetime.datetime.utcfromtimestamp(0))
    if date.tzinfo == None:
        utcDate = pytz.utc.localize(date)
    else:
        utcDate = date
    dateAsSeconds = int((utcDate - utcEpoch).total_seconds())
    return dateAsSeconds

def getDateOfLastScrape():
    fileName = "dateOfLastScrape.txt" # If you change this, change it in
                                      # setDateOfLastScrape too
    try: #if os.path.exists(fileName):
        with open(fileName, 'r') as fin:
            s = fin.readline()
            print("Found " + s + " as the date of the most recent scrape in which a message was found.")
            dateOfLastScrape = datetime.datetime.strptime(s, "%m/%d/%y %H:%M:%S")
    except:
        print("Error accessing " + fileName)
        dateOfLastScrape = datetime.datetime.min
    print()   
    return dateOfLastScrape
    
def setDateOfLastScrape(): #technically, last scrape where we recorded a message
    fileName = "dateOfLastScrape.txt" # If you change this, change it in
                                      # getDateOfLastScrape too
    dateToSet = pytz.utc.localize(datetime.datetime.utcnow())
    dateAsString = dateToSet.strftime("%m/%d/%y %H:%M:%S")
    with open(fileName, 'w') as fout:
        fout.write(dateAsString)
    print()
    print(dateAsString + " recorded as the date of the most recent scrape in which a message was found.")

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
    #printTableSummary(tables)
    """
    printSingleTable("CUSTOMER HOMETOWN", tables[5])
    printSingleTable("CUSTOMER MESSAGE", tables[6])
    printSingleTable("ROOM NAME", tables[9])
    printSingleTable("CHECKIN/OUTS", tables[11], True)
    printSingleTable("NUMBER GUESTS", tables[13])
    printSingleTable("CONFIRMATION CODE", tables[17])
    printSingleTable("TOTAL PRICE", tables[23])
    printSingleTable("OCCUPANCY TAXES", tables[25])
    """
    
    # Parsing
    customerName =      parseCustomerName(msg)
    customerHometown =  parseCustomerHometown(tables)
    customerMessage =   parseCustomerMessage(tables)
    roomName =          parseRoomName(tables)
    (checkInStart, checkInEnd, checkInDate, checkOut, checkOutDate) = \
                        parseCheckInAndOut(tables)
    numberGuests =      parseNumberGuests(tables)
    confirmationCode =  parseConfirmationCode(tables)
    rawPrice =          parseRawPrice(tables)
    serviceFee =        parseServiceFee(tables)
    totalPrice =        parseTotalPrice(tables)
    occupancyTaxes =    parseOccupancyTaxes(tables)

    # Print, maybe
    if VERBOSE:
        print("[Customer Name]",        customerName)
        print("[Customer Hometown]",    customerHometown)
        print("[Customer Message]",     customerMessage)
        print("[Room Name]",            roomName)
        try:
            print("[CheckIn Date]",     checkInDate.date())
        except:
            print("[CheckIn Date]",     checkInDate)
        print("[Checkin Time]",         checkInStart, "-", checkInEnd)
        try:
            print("[CheckOut Date]",    checkOutDate.date())
        except:
            print("[CheckOut Date]",    checkOutDate)
        print("[CheckOut Time]",        checkOut)
        print("[Num Guests]",           numberGuests)
        print("[Confirmation]",         confirmationCode)
        print("[Raw Price]",            rawPrice)
        print("[Service Fee]",          serviceFee)
        print("[Total Price]",          totalPrice)
        print("[Occupancy Taxes]",      occupancyTaxes)
        print()

    # Store data
    #print("Storing parsed fields into json...")
    jsonData = {}
    jsonData["customerName"] =      customerName
    jsonData["customerHometown"] =  customerHometown
    jsonData["customerMessage"] =   customerMessage
    jsonData["roomName"] =          roomName
    jsonData["checkInStart"] =      checkInStart
    jsonData["checkInEnd"] =        checkInEnd
    jsonData["checkInDate"] =       checkInDate.strftime("%m/%d/%Y") #, %H:%M:%S")
    jsonData["checkOut"] =          checkOut
    jsonData["checkOutDate"] =      checkOutDate.strftime("%m/%d/%Y")
    jsonData["numberGuests"] =      numberGuests
    jsonData["confirmationCode"] =  confirmationCode
    jsonData["rawPrice"] =          rawPrice
    jsonData["serviceFee"] =        serviceFee
    jsonData["totalPrice"] =        totalPrice
    jsonData["occupancyTaxes"] =    occupancyTaxes

    return jsonData
    

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
        customerMessage = cMessageParagraph.text.strip()
    except:
        print("Error: could not parse customer message")
    return customerMessage
    
def parseRoomName(tables):
    roomName = "---"
    try:
        roomInformation = tables[9].find("th")
        roomParas = roomInformation.find('p')
        if roomParas == None: # Haha sometimes they switch up the structure of  
                              # the email and the room name will be in the 8th
                              # table instead of the 9th because whyy not :')
            roomInformation = tables[8].find("th")
            roomParas = roomInformation.find('p')
        roomName = roomInformation.find('p').string.strip()[:-1]
    except:
        print("Error: could not parse room name")
    return roomName

def parseCheckInAndOut(tables):
    timeInStart = "---"
    timeInEnd = "---"
    timeOut = "---"
    inDateObj = datetime.date.min
    outDateObj = datetime.date.min
    try:
        # Get a list of the text in our <p> tags
        thList = list(tables[11].find_all("th"))
        if len(thList) < 3:
            thList = list(tables[10].find_all("th"))
        checkinList = list(thList[0].stripped_strings)
        checkoutList = list(thList[2].stripped_strings)
        
        # Check-in parse
        inDate = stripNonAscii(checkinList[1])
        inTime = stripNonAscii(checkinList[2])
        inDateObj = datetime.datetime.strptime(inDate, '%b %d, %Y')
        timeRange = inTime.split("in")[1]
        if "-" in timeRange:
            timeRangeSplit = timeRange.split("-")
            timeInStart = timeRangeSplit[0].strip()
            timeInEnd = timeRangeSplit[1].strip()
        elif "After" in timeRange:
            timeRangeSplit = timeRange.split("After")
            timeInStart = timeRangeSplit[1].strip()
            timeInEnd = "Or Later"
        
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
        numGuestsParas = numGuestsSection.find_all("p")
        if len(numGuestsParas) == 0:
            numGuestsSection = list(tables[12].find_all("th"))[0]
            numGuestsParas = numGuestsSection.find_all("p")
        numberGuests = numGuestsParas[1].text.strip()
    except:
        print("Error: could not parse number of guests")
    return numberGuests

def parseConfirmationCode(tables):
    confirmationCode = "---"
    try:
        confirmationSection = list(tables[17].find_all("th"))[0]
        confirmationCodeParas = list(confirmationSection.find_all("p"))
        if len(confirmationCodeParas) == 0:
            confirmationSection = list(tables[16].find_all("th"))[0]
            confirmationCodeParas = list(confirmationSection.find_all("p"))
        confirmationCode = confirmationCodeParas[1].string.strip()
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
        serviceFeeSection =  list(tables[21].find_all("th"))
        if len(serviceFeeSection) < 2:
            serviceFeeSection =  list(tables[20].find_all("th"))
        serviceFeeParas = serviceFeeSection[1].find("p")
        serviceFee = serviceFeeParas.text.strip()
    except:
        print("Error: could not parse service fee")
    return serviceFee

def parseTotalPrice(tables):
    totalPrice = "---"
    try:
        totalPriceSection = list(tables[23].find_all("th"))
        if len(totalPriceSection) == 2:
            totalPrice = totalPriceSection[1].find("p").string.strip()
        else:
            totalPrice = totalPriceSection[0].find("p").string.strip()
    except:
        print("Error: could not parse total price")
    return totalPrice

def parseOccupancyTaxes(tables):
    occupancyTaxes = "---"
    try:
        occupancyTaxesSection = list(tables[25].find_all("th"))
        occupancyTaxesParas = occupancyTaxesSection[0].find("p")
        if occupancyTaxesParas == None:        
            occupancyTaxesSection = list(tables[24].find_all("th"))
            occupancyTaxesParas = occupancyTaxesSection[0].find("p")
        occupancyTaxesPara = occupancyTaxesParas.string.strip()
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
    print("----------------------------")
    print()

# ------------------------------------------------------------------------------
# ---------------------------------------------------------------------- RUNNING

if __name__ == '__main__':
    while True:
        main()
        print("\n[ SLEEPING 60 SECONDS ]\n")
        time.sleep(60)








        

