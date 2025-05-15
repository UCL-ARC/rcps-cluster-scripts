#!/usr/bin/env python

import os.path
import argparse
import sys
import mysql.connector
from mysql.connector import errorcode
from contextlib import closing
from tabulate import tabulate
import validate
import thomas_queries
import thomas_utils

###############################################################
# user <username>           show all current info for this user
# contacts                  show all allowed values for poc_id
# institutes                show all allowed values for inst_id
# allusers                  show all current users
# getmmm                    show the most recent mmm username used
#
# recentusers <-n N>        show the n newest users (5 by default)
# getusers --project --institute --contact 
# whois --user --email --name --surname
# requests < pending | all | recent <n> >

# custom Action class, must override __call__
class ValidateUser(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # raises a ValueError if the value is incorrect
        validate.user(values)
        setattr(namespace, self.dest, values)
# end class ValidateUser

def getargs(argv):
    parser = argparse.ArgumentParser(description="Show data from the Thomas database. Use [positional argument -h] for more help.")
    parser.add_argument("--user", metavar="username", help="Show all current info for this user", action=ValidateUser)
    parser.add_argument("--contacts", help="Show all allowed values for contact", action='store_true')
    parser.add_argument("--institutes", help="Show all allowed values for institute", action='store_true')
    parser.add_argument("--allusers", help="Show all current users", action='store_true')
    parser.add_argument("--getmmm", help="Show the highest mmm username used", action='store_true')

    # store which subparser was used in args.subcommand
    subparsers = parser.add_subparsers(dest="subcommand")

    # the argument for subcommand recentusers
    recentusers = subparsers.add_parser("recentusers", help="Show the n newest users (5 by default)")
    recentusers.add_argument("-n", type=int, default=5)

    # the arguments for subcommand getusers
    # uses default='%' so all results are kept if that constraint is not used
    getusers = subparsers.add_parser("getusers", help="Show all users with this project, institute, contact", aliases=["users"])
    getusers.add_argument("-p", "--project", dest="project", default='%', help="Project name")
    getusers.add_argument("-i", "--institute", dest="inst_ID", default='%', help="Institute ID")
    getusers.add_argument("-c", "--contact", dest="poc_ID", default='%', help="Point of Contact ID")    

    # the arguments for subcommand whois
    # not validating username as this can be partial
    whois = subparsers.add_parser("whois", help="Search for users matching the given requirements")
    whois.add_argument("-u", "--user", dest="username", default='', help="UCL username of user contains")
    whois.add_argument("-e", "--email", dest="email", default='', help="Email address of user contains")
    whois.add_argument("-n", "--name", dest="given_name", default='', help="Given name of user contains")
    whois.add_argument("-s", "--surname", dest="surname", default='', help="Surname of user contains")
 
    # the arguments for subcommand requests
    requests = subparsers.add_parser("requests", help="Show account requests (default is all pending requests)")
    requests.add_argument("--pending", help="Show all (non-test) pending requests", action='store_true')
    requests.add_argument("--all", help="Show all requests", action='store_true')
    requests.add_argument("--test", help="Show test requests", action='store_true')

    # to choose the number of requests to show, including a default,
    # it seems we need another subparser
    requestsubparsers = requests.add_subparsers(dest="requestsubcommand")
    recent = requestsubparsers.add_parser("recent", help="Show n most recent requests (default 5)")
    recent.add_argument("-n", type=int, default=5)

    # Show the usage if no arguments are supplied
    if len(argv) < 1:
        parser.print_usage()
        exit(1)

    # return the arguments
    # contains only the attributes for the main parser and the subparser that was used
    return parser.parse_args(argv)
# end getargs

# Simplest possible outputting of query result without brackets
# (Just printing the fetchall results shows structure like ('a','b','c'))
def simpleprint(results):
    for row in results:
        print (row[0])
    print("")

# Write out results as a table with header and separators
def tableprint(cursor, results):
    columns = (d[0] for d in cursor.description)
    print(tabulate(results, headers=columns, tablefmt="psql"))
    print("")

# Get user info (not ssh key as it is huge)
def userinfo(cursor, args_dict):
    query = thomas_queries.userinfo()
    cursor.execute(query, args_dict)
    return cursor

# Get ssh key on file
def sshinfo(cursor, args_dict):
    query = thomas_queries.sshinfo()
    cursor.execute(query, args_dict)
    return cursor

# Get all of user's projects and related points of contact
def projectinfo(cursor, args_dict):
    query = thomas_queries.projectinfo()
    cursor.execute(query, args_dict)
    return cursor

# Get all points of contact and their username if they have one.
def contactsinfo(cursor):
    query = thomas_queries.contactstatusinfo()
    cursor.execute(query)
    return cursor

# Get all institutes
def instituteinfo(cursor):
    query = thomas_queries.instituteinfo()
    cursor.execute(query)
    return cursor

# Get all existing users (username, names, email, dates but not ssh keys)
def alluserinfo(cursor):
    query = thomas_queries.alluserinfo()
    cursor.execute(query)
    return cursor

# Get the n latest users (not ssh keys). Default n provided by argparser.
def recentinfo(cursor, args_dict):
    query = thomas_queries.recentinfo()
    cursor.execute(query, args_dict)
    return cursor

# Get the most recent mmm username used - sorting by username as well as date
# in case of identical timestamps.
def lastmmm(cursor):
    query = thomas_queries.lastmmm()
    cursor.execute(query)
    return cursor

# Get all users in this project/inst/PoC combo
# Need to use LIKE so can match all by default with % when an option is not specified
def projectcombo(cursor, args_dict):
    query = thomas_queries.projectcombo()
    cursor.execute(query, args_dict)
    return cursor

# Allowing partial matches with %username%.
# The default is a blank, so ends up as %% which matches all
def whoisuser(cursor, args_dict):
    query = thomas_queries.whoisuser()
    #query = ("SELECT username, givenname, surname, email, status, creation_date, modification_date FROM users WHERE username LIKE '{}' AND email LIKE '{}' AND givenname LIKE '{}' AND surname LIKE '{}'").format("%" + args_dict["username"] + "%", "%" + args_dict["email"] + "%", "%" + args_dict["given_name"] + "%", "%" + args_dict["surname"] + "%")
    cursor.execute(query, ("%" + args_dict["username"] + "%", "%" + args_dict["email"] + "%", "%" + args_dict["given_name"] + "%", "%" + args_dict["surname"] + "%"))
    return cursor

# Get all pending account requests 
# ('is not true' will pick up any nulls, though there shouldn't be any).
def pendingrequests(cursor, args_dict):
    query = thomas_queries.pendingrequests()
    cursor.execute(query, args_dict)
    return cursor

# Get all existing requests and also display the user's names.
def allrequests(cursor):
    query = thomas_queries.allrequests() 
    cursor.execute(query)
    return cursor

# Get the n most recent requests, in any state. Default n provided by argparser.
def recentrequests(cursor, args_dict):
    query = thomas_queries.recentrequests()
    cursor.execute(query, args_dict)
    return cursor

# Get the account requests, print if appropriate
def showrequests(cursor, args, args_dict, printoutput):
    if (args.all):
        results = allrequests(cursor).fetchall()
    elif (args.requestsubcommand == "recent"):
        results = recentrequests(cursor, args_dict).fetchall()
    elif (args.test):
        cursor.execute(thomas_queries.pendingtestrequests())
        results = cursor.fetchall()
    # if pending or not specified, show pending
    else: 
        results = pendingrequests(cursor, args_dict).fetchall()

    if (printoutput):
        tableprint(cursor, results)
    return results


# Put main in a function so it is importable.
def main(argv, printoutput):

    # check which MMM cluster we are on and pick the correct db to connect to.
    nodename = thomas_utils.getnodename()
    db = thomas_utils.getdb(nodename)

    try:
        args = getargs(argv)
        args.cluster = thomas_utils.getcluster(nodename)
        # make a dictionary from args to make string substitutions doable by key name
        args_dict = vars(args)
    except ValueError as err:
        print(err, file=sys.stderr)
        exit(1)
    # connect to MySQL database with read access.
    # (.thomas.cnf has readonly connection details as the default option group)

    try:
        #conn = mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), database=db)
        #cursor = conn.cursor()
        # make sure we close the connection wherever we exit from
        with closing(mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), database=db)) as conn, closing(conn.cursor()) as cursor:

            # Get info for the given user, print if running directly.
            # Fetchall removes the rows from the cursor, but the description is still there
            # so the cursor must also be passed to tableprint to print the headers.
            if (args.user is not None):
                userresults = userinfo(cursor, args_dict).fetchall()
                if (printoutput):
                    print("All information for {}:".format(args.user))
                    tableprint(cursor, userresults)

                sshresults = sshinfo(cursor, args_dict).fetchall()
                if (printoutput):
                    print("SSH key on file:")
                    simpleprint(sshresults)

                projectresults = projectinfo(cursor, args_dict).fetchall()
                if (printoutput):
                    print("User is in these projects:")
                    tableprint(cursor, projectresults)
                return (userresults, sshresults, projectresults)

            # Get all allowed values for poc_id
            if (args.contacts):
                contactresults = contactsinfo(cursor).fetchall()
                if (printoutput):
                    print("All current Points of Contact:")
                    tableprint(cursor, contactresults)
                return contactresults      
 
            # Get all allowed values for inst_id
            if (args.institutes):
                instresults = instituteinfo(cursor).fetchall()
                if (printoutput):
                    print("All current institutes:")
                    tableprint(cursor, instresults)
                return instresults

            # Get all existing users (username, names, email, dates but not ssh keys)
            if (args.allusers):
                alluserresults = alluserinfo(cursor).fetchall()
                if (printoutput):
                    print("All current users:")
                    tableprint(cursor, alluserresults)
                return alluserresults

            # Get the n latest users (not ssh keys)
            if (args.subcommand == "recentusers"):
                recentresults = recentinfo(cursor, args_dict).fetchall()
                if (printoutput):
                    tableprint(cursor, recentresults)
                return recentresults

            # Get the most recent mmm user added    
            if (args.getmmm):        
                lastresult = lastmmm(cursor).fetchall()
                if (printoutput):
                    simpleprint(lastresult)
                # This is a list of tuples with one element - returning the string is more useful
                return lastresult[0][0]

            # Get all users in this project/inst/PoC combo
            if (args.subcommand == "getusers") or (args.subcommand == "users"):
                comboresults = projectcombo(cursor, args_dict).fetchall()
                if (printoutput):
                    tableprint(cursor, comboresults)
                return comboresults

            # Who is this person?
            if (args.subcommand == "whois"):
                whoisresults = whoisuser(cursor, args_dict).fetchall()
                if (printoutput):
                    tableprint(cursor, whoisresults)
                return whoisresults
        
            # Get account requests
            if (args.subcommand == "requests"):
                return showrequests(cursor, args, args_dict, printoutput)


    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err, file=sys.stderr)
    else:
        cursor.close()
        conn.close()
# end main

# When not imported, set print to True
if __name__ == "__main__":
    main(sys.argv[1:], True)

