#!/usr/bin/env python

import os.path
import argparse
import sys
from email.mime.text import MIMEText
import subprocess
from subprocess import Popen, PIPE
import csv
import mysql.connector
from mysql.connector import errorcode
from contextlib import closing
import socket
import validate
import thomas_show
import thomas_create
import thomas_utils
import thomas_queries

###############################################################
# Subcommands:
# user, project, projectuser, poc, institute
#
# --debug			show SQL query submitted without committing the change

# custom Action class, must override __call__
class ValidateUser(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # raises a ValueError if the value is incorrect
        validate.user(values)
        setattr(namespace, self.dest, values)
# end class ValidateUser

def getargs(argv):
    parser = argparse.ArgumentParser(description="Add data to the MMM user database. Use [positional argument -h] for more help.")
    # store which subparser was used in args.subcommand
    subparsers = parser.add_subparsers(dest="subcommand")

    # the arguments for subcommand 'csv'
    csvparser = subparsers.add_parser("csv", help="Add all users from the provided CSV file")
    csvparser.add_argument("-f", "--file", dest="csvfile", help="Path to CSV file of users", required=True)
    csvparser.add_argument("--noconfirm", help="Don't ask for confirmation on user account creation", action='store_true')
    csvparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    csvparser.add_argument("--nosupportemail", help="Do not email rc-support to create this account", action='store_true')
    csvparser.add_argument("--debug", help="Show SQL queries submitted without committing the changes", action='store_true')
    csvparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # the arguments for subcommand 'user'
    userparser = subparsers.add_parser("user", help="Adding a new user with their initial project")
    userparser.add_argument("-u", "--user", dest="username", help="UCL username of user", action=ValidateUser)
    userparser.add_argument("-n", "--name", dest="given_name", help="Given name of user", required=True)
    userparser.add_argument("-s", "--surname", dest="surname", help="Surname of user (optional)")
    userparser.add_argument("-e", "--email", dest="email", help="Institutional email address of user", required=True)
    userparser.add_argument("-k", "--key", dest="ssh_key", help="User's public ssh key (quotes necessary)", required=True)
    userparser.add_argument("-p", "--project", dest="project_ID", help="Initial project the user belongs to", required=True)
    userparser.add_argument("-c", "--contact", dest="poc_id", help="Short ID of the user's Point of Contact", required=True)
    userparser.add_argument("--noconfirm", help="Don't ask for confirmation on user account creation", action='store_true')
    userparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    userparser.add_argument("--nosshverify", help="Do not verify SSH key (use with caution!)", action='store_true')
    userparser.add_argument("--nosupportemail", help="Do not email rc-support to create this account", action='store_true')
    userparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')
    userparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # the arguments for subcommand 'project'
    projectparser = subparsers.add_parser("project", help="Adding a new project")
    projectparser.add_argument("-p", "--project", dest="project_ID", help="A new unique project ID", required=True)
    projectparser.add_argument("-i", "--institute", dest="inst_ID", help="Institute ID this project belongs to", required=True)
    projectparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    projectparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')
    projectparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # the arguments for subcommand 'projectuser'
    projectuserparser = subparsers.add_parser("projectuser", help="Adding a new user-project-contact relationship")
    projectuserparser.add_argument("-u", "--user", dest="username", help="An existing UCL username", required=True, action=ValidateUser)
    projectuserparser.add_argument("-p", "--project", dest="project_ID", help="An existing project ID", required=True)
    projectuserparser.add_argument("-c", "--contact", dest="poc_id", help="An existing Point of Contact ID", required=True)
    parser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    projectuserparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')
    projectuserparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # the arguments for subcommand 'poc'
    pocparser = subparsers.add_parser("poc", help="Adding a new Point of Contact")
    pocparser.add_argument("-p", "--poc_id", dest="poc_id", help="Unique PoC ID, in form N(ame)N(ame)_instituteID", required=True)
    pocparser.add_argument("-n", "--name", dest="given_name", help="Given name of PoC", required=True)
    pocparser.add_argument("-s", "--surname", dest="surname", help="Surname of PoC (optional)")
    pocparser.add_argument("-e", "--email", dest="email", help="Email address of PoC", required=True)
    pocparser.add_argument("-i", "--institute", dest="inst_ID", help="Institute ID of PoC", required=True)
    pocparser.add_argument("-u", "--user", dest="username", help="The PoC's UCL username (optional)", action=ValidateUser)
    pocparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    pocparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')
    pocparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # the arguments for subcommand 'institute'
    instituteparser = subparsers.add_parser("institute", help="Adding a new institute/consortium")
    instituteparser.add_argument("-i", "--id", dest="inst_ID", help="Unique institute ID, eg QMUL, Imperial, Soton", required=True)
    instituteparser.add_argument("-n", "--name", dest="institute", help="Full name of institute/consortium", required=True)
    instituteparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    instituteparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')
    instituteparser.add_argument("--livedebug", help="Carry everything out but show extra information about where in the code we are", action='store_true')

    # Show the usage if no arguments are supplied
    if len(argv) < 1:
        parser.print_usage()
        exit(1)

    # return the arguments
    # contains only the attributes for the main parser and the subparser that was used
    return parser.parse_args(argv)
# end getargs

# Return the next available mmm username (without printing result).
# mmm usernames are in the form mmmxxxx, get the integers and increment
def nextmmm():
    latestmmm = thomas_show.main(['--getmmm'], False)
    mmm_int = int(latestmmm[-4:]) + 1
    # pad to four digits with leading zeroes, giving a string
    mmm_string = '{0:04}'.format(mmm_int)
    return 'mmm' + mmm_string

# send an email to RC-Support with the command to run to create this account,
# unless debugging in which case just print it.
# By default, assumes this is not a CSV multi-user creation (csv and num are optional).
# NOT CURRENTLY CALLED EXCEPT ON THOMAS - REMOVED BY AUTOMATION
def contact_rc_support(args, request_id, csv='no', num=1):
    if (args.livedebug):
        print("-- start thomas_add.contact_rc_support")
    if csv == 'no':
        body = (args.cluster.capitalize() + """ user account request id """ + str(request_id) + """ has been received.""")
    else:
        body = (args.cluster.capitalize() + """ multi-user account request has been received for """ + str(num) + """ users, last request id """ + str(request_id) + """. """)
    body += ("""
Please run '""" + args.cluster + """-show requests' on a """ + args.cluster.capitalize() + """ login node to see pending requests.
Requests can then be approved by running '""" + args.cluster + """-create request id1 [id2 id3 ...]'

""")

    msg = MIMEText(body)
    msg["From"] = "service-management-noreply@ucl.ac.uk"
    msg["To"] = "rc-support@ucl.ac.uk"
    msg["Subject"] = args.cluster.capitalize() + " account request"
    if (args.debug):
        print("")
        print("Email that would be sent:")
        print(msg)
    else:
        p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE, universal_newlines=True)
        p.communicate(msg.as_string())
        print("RC Support has been notified to create the account(s).")
# end contact_rc_support

# query to run to get PoC email address
def run_poc_email():
    query = ("""SELECT poc_email FROM pointofcontact WHERE poc_id=%(poc_id)s""")
    return query

# get poc_id of submitter, or prompt to pick one
def get_poc_id(cursor, args, args_dict):
    if (args.livedebug):
        print("-- start thomas_add.get_poc_id")
    me = os.environ.get('USER')
    # check if I am a PoC
    cursor.execute(thomas_queries.findpocbyusername(), {'username': me})
    results = cursor.fetchall()
    rows_count = cursor.rowcount
    # I am a PoC and unique
    if rows_count == 1:
        #result = dict(zip(cursor.column_names, results[0]))
        result = results[0]
        args_dict['poc_id'] = result['poc_id']
        return True
    # I am more than one PoC
    elif rows_count > 1:
        # pick one
        data = results
        # results are already a list of dictionaries, keys being db column names.
        for i in range(rows_count):
            #data.append(dict(list(zip(cursor.column_names, results[i]))))
            # while we do this, print out the results, numbered.
            print(str(i+1) + ") "+ data[i]['poc_id'] +", "+ data[i]['poc_givenname'] +" "+ data[i]['poc_surname'] +", "+ data[i]['institute'] + ", status: " + data[i]['status'])

        # make a string list of options, counting from 1 and ask the user to pick one
        options_list = [str(x) for x in range(1, rows_count+1)]
        response = thomas_utils.select_from_list("\nPlease choose which point of contact ID to use for these user account requests. \n Please respond with a number in the list or n for none.", options_list)
        if response == "n":
            print("None chosen, showing all points of contact.")
        else:
            # go back to zero-index, get chosen username
            args_dict['poc_id'] = data[int(response)-1]['poc_id']
            print("Using Point of Contact ID " + args_dict['poc_id'])
            return True
        
    # no matches or none chosen - ask to pick from whole list
    cursor.execute(thomas_queries.contactstatusinfo())
    results = cursor.fetchall()
    rows_count = cursor.rowcount
    data = results
    # results are already a list of dictionaries, keys being db column names.
    for i in range(rows_count):
        #data.append(dict(list(zip(cursor.column_names, results[i]))))
        # while we do this, print out the results, numbered.
        print(str(i+1) + ") "+ data[i]['poc_id'] +", "+ data[i]['poc_givenname'] +" "+ data[i]['poc_surname'] +", "+ data[i]['institute'] + ", status: " + data[i]['status'])

    # make a string list of options, counting from 1 and ask the user to pick one
    options_list = [str(x) for x in range(1, rows_count+1)]
    response = thomas_utils.select_from_list("\nPlease choose which point of contact ID to use for these user account requests. \n Please respond with a number in the list or n for none.", options_list)
    if response == "n":
        print("None chosen, doing nothing and exiting.")
        exit(0)
    else:
        # go back to zero-index, get chosen username
        args_dict['poc_id'] = data[int(response)-1]['poc_id']
        print("Using Point of Contact ID " + args_dict['poc_id'])
        return True
# end get_poc_id

# everything needed to create a new account creation request
def create_user_request(cursor, args, args_dict):
    if (args.livedebug):
        print("-- start thomas_add.create_user_request")
    # projectusers status is pending until the request is approved
    args_dict['status'] = "pending"
    # add a project-user entry for the user
    cursor.execute(thomas_queries.addprojectuser(), args_dict)
    debug_cursor(cursor, args)
    # get the poc_email and add to dictionary
    cursor.execute(run_poc_email(), args_dict)
    poc_email = cursor.fetchall()[0]['poc_email']
    args_dict['poc_email'] = poc_email
    # add the account creation request to the database
    cursor.execute(thomas_queries.addrequest(), args_dict)
    # lastrowid is the autoincrement id from this cursor's last INSERT statement
    request_id = cursor.lastrowid
    debug_cursor(cursor, args)
    return request_id
# end create_user_request

# everything needed to create a new user
def create_new_user(cursor, args, args_dict):
    if (args.livedebug):
        print("-- start thomas_add.create_new_user")
    # if no username was specified, get the next available mmm username
    if (args.username == None or args_dict['username'] == ''):
        args.username = nextmmm()
        args_dict['username'] = args.username
    # users status is pending until the request is approved
    args_dict['status'] = "pending"
    # confirm that info is ok unless --noconfirm is set
    if not args.noconfirm:
        if not thomas_utils.are_you_sure("\nDo you want to create the user account with this information? \n    Username: "+args.username+"\n    Email: "+args.email+ "\n    SSH key: "+args.ssh_key+"\n"):
            print("Entry rejected: doing nothing and exiting.")
            exit(0)
  
    print("")
    # insert new user into users table      
    cursor.execute(thomas_queries.adduser(args.surname), args_dict)
    debug_cursor(cursor, args)
    # create the account creation request and get the request id (as a list)
    create_user_request(cursor, args, args_dict)
    #args.request = [create_user_request(cursor, args, args_dict)]
    # automated creation - go straight to approval
    #args.noemail = False
    #thomas_create.approverequest(args, args_dict, cursor, thomas_utils.getnodename())
# end create_new_user

# Check for duplicate users by key: email or username
def check_dups(key_string, cursor, args, args_dict):
    if (args.livedebug):
        print("-- start thomas_add.check_dups")
    cursor.execute(thomas_queries.findduplicate(key_string), args_dict)
    results = cursor.fetchall()
    rows_count = cursor.rowcount
    if rows_count > 0:
        # We have duplicate(s). Show results and ask them to pick one or none
        print(str(rows_count) + " user(s) with this " +key_string+ " already exist:\n")
        data = results
        # With dictionary cursor, results are already a list of dicts
        for i in range(rows_count):
            #data.append(dict(list(zip(cursor.column_names, results[i]))))
            # print out the results, numbered from 1.
            print(str(i+1) + ") "+ data[i]['username'] +", "+ data[i]['givenname'] +" "+ data[i]['surname'] +", "+ data[i]['email'] + ", created " + str(data[i]['creation_date']))

        # make a string list of options, counting from 1 and ask the user to pick one
        options_list = [str(x) for x in range(1, rows_count+1)]
        response = thomas_utils.select_from_list("\nDo you want to add a new project to one of the existing accounts instead? \n(You should do this if it is the same individual). \n Please respond with a number in the list or n for none.", options_list)

        # said no to using existing user
        if response == "n":
            # can create a duplicate if it is *not* a username duplicate
            if key_string != "username":
                if thomas_utils.are_you_sure("Do you want to create a second account with that "+key_string+"?"):
                    # create new duplicate user
                    create_new_user(cursor, args, args_dict)
                    return True
                # said no to everything
                else: 
                    print("No second account requested, doing nothing and exiting.")
                    exit(0)
            # Was a username duplicate
            else:
                print("Username in use, doing nothing and exiting.")
                exit(0) 
        # picked an existing user
        else:
            # go back to zero-index, get chosen username
            args.username = data[int(response)-1]['username']
            print("Using existing user " + args.username)
            create_user_request(cursor, args, args_dict) 
            return True

    # there were no duplicates and we did nothing
    return False
# end check_dups

# run all this when someone tries to create a new user
# for now we are assuming the creation request was done on the correct cluster
def new_user(cursor, args, args_dict):
    if (args.livedebug):
        print("-- start thomas_add.new_user")
    # if there was no duplicate username check for duplicate email
    if not check_dups("username", cursor, args, args_dict):
        if not check_dups("email", cursor, args, args_dict):
            # no duplicates at all, create new user
            create_new_user(cursor, args, args_dict)

# end new_user

def debug_cursor(cursor, args):
    if (args.verbose or args.debug):
        print(cursor.statement)

# Put main in a function so it is importable.
def main(argv):

    # get the name of this cluster and the MMM db to connect to
    nodename = thomas_utils.getnodename()
    db = thomas_utils.getdb(nodename)

    # get all the parsed args
    try:
        args = getargs(argv)
        # add cluster name to args
        args.cluster = thomas_utils.getcluster(nodename)
        # make a dictionary from args to make string substitutions doable by key name
        args_dict = vars(args)
    except ValueError as err:
        print(err)
        exit(1)

    # Check that the user running the add command is a member of ccsprcop or lgmmmpoc or ag-archpc-mmm-poc-tools
    #if not validate.user_has_privs():
    #    print("You need to be a member of the lgmmmpoc or ccsprcop groups to run the add commands. Exiting.", file=sys.stderr)
    #    exit(1)

    if (args.subcommand == "user"):
        # UCL user validation - if this is a UCL email, make sure username was given 
        # and that it wasn't an mmm one.
        validate.ucl_user(args.email, args.username)
        # Unless nosshverify is set, verify the ssh key
        if (args.nosshverify == False):
            validate.ssh_key(args.ssh_key)
            if (args.verbose or args.debug):
                print("")
                print("SSH key verified.")
                print("")

    # connect to MySQL database with write access.
    # (.thomas.cnf has readonly connection details as the default option group)

    try:
        #conn = mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), option_groups='thomas_update', database=db)
        # make sure we close the connection wherever we exit from
        with closing(mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), option_groups='thomas_update', database=db)) as conn, closing(conn.cursor(dictionary=True)) as cursor:
            #cursor = conn.cursor()

            if (args.verbose or args.debug):
                print("")
                print(">>>> Queries being sent:")

            # CSV file was provided
            if (args.subcommand == "csv"):
                # Get poc_id for submitter, or prompt
                get_poc_id(cursor, args, args_dict)
                args.poc_id = args_dict['poc_id']
                with open(args.csvfile) as input:
                    reader = csv.DictReader(input, delimiter=',')
                    num_users = 0
                    for row_dict in reader:
                        args.username = row_dict['username']
                        args.surname = row_dict['surname']
                        row_dict['poc_id'] = args_dict['poc_id']
                        row_dict['cluster'] = args_dict['cluster']
                        new_user(cursor, args, row_dict)
                        num_users += 1

            # cursor.execute takes a querystring and a dictionary or tuple
            elif (args.subcommand == "user"):
                new_user(cursor, args, args_dict)

            elif (args.subcommand == "projectuser"):
                # This is an existing user, status for the new project-user pairing is active by default
                args_dict['status'] = "active"
                cursor.execute(thomas_queries.addprojectuser(), args_dict)
                debug_cursor(cursor, args)
            elif (args.subcommand == "project"):
                cursor.execute(thomas_queries.addproject(), args_dict)
                debug_cursor(cursor, args)
            elif (args.subcommand == "poc"):
                args_dict['status'] = "active"
                cursor.execute(thomas_queries.addpoc(args.surname, args.username), args_dict)
                debug_cursor(cursor, args)
            elif (args.subcommand == "institute"):
                cursor.execute(thomas_queries.addinstitute(), args_dict)
                debug_cursor(cursor, args)

            # commit the change to the database unless we are debugging
            if (not args.debug):
                if (args.verbose):
                    print("")
                    print("Committing database change")
                    print("")
                conn.commit()

            # Databases are updated, now email rc-support unless nosupportemail is set
            # (only email on Thomas)
            if not args.cluster == "thomas":
                args.nosupportemail = True
            if (args.subcommand == "user" and args.nosupportemail == False):
                # get the last id added (which is from the requests table)
                # this has to be run after the commit
                last_id = cursor.lastrowid
                contact_rc_support(args, last_id)
            elif (args.subcommand == "csv" and args.nosupportemail == False):
                last_id = cursor.lastrowid
                contact_rc_support(args, last_id, csv='yes', num=num_users)

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: Something is wrong with your user name or password", file=sys.stderr)
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist", file=sys.stderr)
        else:
            print(err, file=sys.stderr)
    else:
        cursor.close()
        conn.close()
# end main

# When not imported, use the normal global arguments
if __name__ == "__main__":
    main(sys.argv[1:])

