# Utility functions used in multiple places in the thomas tools.

from tabulate import tabulate
from ldap3 import Server, Connection, ALL
import socket
import thomas_queries
import validate
import subprocess
import sys

##########################
#                        #
# Get last/next username #
#                        #
##########################

# Given a username as a string, get the next one
# mmm usernames are in the form mmmxxxx
def nextmmm(latestmmm):
    mmm_int = int(latestmmm[-4:]) + 1
    # pad to four digits with leading zeroes, giving a string
    mmm_string = '{0:04}'.format(mmm_int)
    return 'mmm' + mmm_string

# Get the most recent mmm username used from the database
def lastmmm(cursor):
    cursor.execute(thomas_queries.lastmmm())
    lastresult = cursor.fetchall()
    # I am using a dictionary cursor, otherwise this would be a list of tuples.
    # This is a list of dictionaries with one element - returning the string is more useful
    return lastresult[0]['username']

# Get the next unused mmm username
def getunusedmmm(cursor):
    return nextmmm(lastmmm(cursor))

#####################################
#                                   #
# Check for duplicate user by email #
#                                   #
#####################################

def findduplicate(cursor, email_address):
    return cursor.execute(thomas_queries.findduplicate(), dict(email=email_address))

###############################
#                             #
# Find a point of contact ID  #
#                             #
###############################

# poc_dict needs to contain 'poc_lastname', 'poc_email' and may contain 'project_ID'.
def findpocID(cursor, poc_dict):
    # check for email match, filtered by project_ID as long as it
    # was in the dictionary and not None, empty or blank string.
    project = poc_dict.get('project_ID')
    if project and project.strip():
        # use the first part of the project_ID up to any underscore as institute
        findpocIDbyemail(cursor, poc_dict['poc_email'], inst=project.partition("_")[0])
    else:
        findpocIDbyemail(cursor, poc_dict['poc_email'])
    result = cursor.fetchall()
    rowcount = cursor.rowcount
    # no result, check surname match
    if rowcount == 0:
        findpocIDbysurname(cursor, poc_dict['poc_lastname'])
        result = cursor.fetchall()
        rowcount = cursor.rowcount
    # still no result, get whole PoC list
    if rowcount == 0:
        cursor.execute(thomas_queries.contactsinfo())
        result = cursor.fetchall()
        rowcount = cursor.rowcount
    # now we have some results, check if one or many and return the user's choice
    return searchpocresults(result, rowcount)
# end findpocID


# Either return the single matching poc_id or ask the user to pick from several
def searchpocresults(result, rowcount):
    if rowcount == 1:
        print("Match for point of contact found: " + result[0]['poc_givenname'] + " " + result[0]['poc_surname'] + ", " + result[0]['poc_id'])
        return result[0]['poc_id']
    # found multiple matches, ask
    elif rowcount > 1:
        # make a list of strings 1, 2, etc to choose from
        options_list = [str(x) for x in range(1, rowcount+1)] 
        for i in range(rowcount):
            # print the results, labeled from 1
            print(options_list[i] + ") "+ result[i]['poc_givenname'] +" "+ result[i]['poc_surname'] + ", " + result[i]['poc_id'])
        response = select_from_list("Please choose the correct point of contact or n for none.", options_list)
        # user said no to all options
        if response == "n":
            print("No point of contact chosen, doing nothing and exiting.")
            exit(0)
        # picked an option
        else:
            # go back to zero-index, return chosen poc_id
            poc_id = result[int(response)-1]['poc_id']
            print(poc_id + " chosen.")
            return poc_id
    # no results were passed in
    else:
        print("Zero rows of points of contact found.", file=sys.stderr)
        exit(1)
# end searchpocresults

# inst is an optional filter
def findpocIDbyemail(cursor, email, inst=None):
    if inst is not None:
        cursor.execute(thomas_queries.findpocbyemailandinst(), {'poc_email':email, 'institute':inst})
    else:
        cursor.execute(thomas_queries.findpocbyemail(), {'poc_email':email})

def findpocIDbysurname(cursor, surname):
    cursor.execute(thomas_queries.findpocbylastname(), {'poc_surname':surname})


#################################
#                               #
# Print functions and debugging #
#                               #
#################################

# Simplest possible outputting of query result without brackets
# (Just printing the fetchall results shows structure like ('a','b','c'))
def simpleprint(results):
    for row in results:
        print (row[0])
    print("")

# Write out results from cursor.fetchall() as a table with
# headers and separators. 
# Assumes a dictionary cursor: conn.cursor(dictionary=True)
def tableprint_dict(results):
    print(tabulate(results, headers="keys", tablefmt="psql"))
    print("")

# Write out results as a table with header and separators
def tableprint(cursor, results):
    columns = (d[0] for d in cursor.description)
    print(tabulate(results, headers=columns, tablefmt="psql"))
    print("")

# Print out the cursor statement for debugging purposes
def debugcursor(cursor, debug):
    if (debug):
        print(cursor.statement)

######################
#                    #
# Database additions #
#                    #
######################

# Add a new user to the database.
def addusertodb(args, args_dict, cursor):
    cursor.execute(thomas_queries.adduser(args.surname), args_dict)
    debugcursor(cursor, args.debug)

# Add a new project-user relationship to the database
def addprojectuser(args, args_dict, cursor):
    cursor.execute(thomas_queries.addprojectuser(), args_dict)
    debugcursor(cursor, args.debug)

def addproject(args, args_dict, cursor):
    cursor.execute(thomas_queries.addproject(), args_dict)
    debugcursor(cursor, args.debug)

##############
#            #
# User input #
#            #
##############

# Interactive confirmation - asks for yes/no input.
# default_ans can be True, False, None
def are_you_sure(question, default_ans=False):
    yes_list = ["yes", "y"]
    no_list = ["no", "n"]

    # Input hint shows whether there is a default
    defaults = { None:"[y/n]", True:"[Y]", False:"[N]" }
    # assemble prompt string
    prompt = "%s %s: " %(question, defaults[default_ans])

    # get answer in lower case. If no default, loops until valid input received.
    while True:
        try:
            confirm = input(prompt).lower()
        except KeyboardInterrupt:
            return False
        if not confirm and default_ans is not None:
            return default_ans
        if confirm in yes_list:
            return True
        if confirm in no_list:
            return False

        # invalid input received
        reprompt = "Please respond with y or n"
        print(reprompt)
# end of are_you_sure

# Interactive confirmation, choose from list.
# Note: answers_list should be a list of strings or the input
# comparison won't work. 
def select_from_list(question, answers_list, default_ans="n"):
    # assemble prompt string
    prompt = "%s [Default=%s]: " %(question, default_ans) 
    #print(answers_list)

    # get answer in lower case. If no default, loops until valid input received.
    while True:
        try:
            answer = input(prompt).lower()
        except KeyboardInterrupt:
            return False
        # they just pressed return, use the default
        if not answer and default_ans is not None:
            return default_ans
        # they picked a valid answer
        if answer == default_ans or answer in answers_list:
            return answer

        # invalid input received
        reprompt = "Please respond with an option in the list or the default."
        print(reprompt)
# end of select_from_list

#########################################
#                                       #
# Make sure you're on the right cluster #
#                                       #
#########################################

def checkprojectoncluster(project, nodename):
    # If this is a Faraday project and this isn't Michael, ask for confirmation.
    if (project.startswith("Faraday")):
        if "michael" not in nodename:
            answer = are_you_sure("You are trying to create project "+project+" on "+nodename+" which is not Michael.\n Do you want to continue?", False)
            # they said no, exit
            if not answer:
                exit(1)
    # If this isn't a Faraday project and this is Michael, ask for confirmation.
    elif ("michael" in nodename):
        answer = are_you_sure("You are trying to create project "+project+" which does not begin with Faraday on "+nodename+".\n Do you want to continue?", False)
        # they said no, exit
        if not answer:
            exit(1)
# end checkprojectoncluster

def getnodename():
    # if /opt/sge/default/common/cluster_name exists, use that
    try:
        with open('/opt/sge/default/common/cluster_name', 'r') as f:
            nodename = f.read().rstrip()
    except IOError as _:
        # fall back to getfqdn
        nodename = socket.getfqdn().casefold()
    return nodename

def getcluster(nodename):
    if "thomas" in nodename:
        return "thomas"
    elif "michael" in nodename:
        return "michael"
    elif "young" in nodename:
        return "young"
    else:
        print("Cluster not recognised, nodename is "+nodename, file=sys.stderr)
        exit(1)
# end getcluster

# get the correct MMM db to connect to for this cluster
def getdb(nodename):
    if "young" in nodename:
        db = "young"
    else:
        db = "thomas"
    return db

#########################
#                       #
# Get user info from AD #
#                       #
#########################

def AD_username_from_email(config, email):
# TODO: add some exception-handling here
    # using ldaps:// in the host gets it to use SSL
    server = Server(config['ad']['host'], get_info=ALL)
    conn = Connection(server, user=config['ad']['user'], password=config['ad']['password'], auto_bind=True)
    # the filter string has to include the brackets: (mail=email)
    filter='(mail=' + email + ')'
    conn.search('DC=ad,DC=ucl,DC=ac,DC=uk', filter, attributes=['cn'])
    # check if we got more than one result (bad!)
    # TODO: ask if we want to pick one
    if len(conn.entries[0].cn.values) > 1 or len(conn.entries) > 1:
        print("More than one username found for " + email + ", exiting.", file=sys.stderr)
        print(conn.entries)
        exit(1)
    return conn.entries[0].cn.values[0]

#################################
#                               #
# Add SSH key to user's account #
#                               #
#################################

def addsshkey(username, key, args): 
    # runs bash script (also in rcps-cluster-scripts) to become user and 
    # add key to their ~/.ssh/authorized_keys 

    # first verify ssh key
    validate.ssh_key(key)

    key_args = ['addsshkey', username, key]

    if (args.debug):
        print("Arguments that would be used:")
        return print(key_args)
    else:
        return subprocess.check_call(key_args) 

#################################
#                               #
# Run external Gold scripts     #
#                               #
#################################

def transfergold(source_id, source_alloc_id, project_code, description, amount, args):

    # make sure source_id, source_alloc_id, amount are strings
    if not isinstance(source_id, str):
        source_id = str(source_id)
    if not isinstance(source_alloc_id, str):
        source_alloc_id = str(source_alloc_id)
    if not isinstance(amount, str):
        amount = str(amount)

    transfer_args = ['transfergold', '-i', source_id, '-a', source_alloc_id, '-p', project_code, '-t', description, '-g', amount]

    if (args.debug):
        print("Arguments that would be used:")
        return print(transfer_args)
    else:
        return subprocess.check_call(transfer_args)


def refreshSAFEgold(args):

    refresh_args = ['refreshsafegold']
    if (args.debug):
        print("Command that would be used:")
        return print(refresh_args)
    else:
        return subprocess.check_call(refresh_args)


