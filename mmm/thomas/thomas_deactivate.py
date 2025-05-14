#!/usr/bin/env python

import os.path
import argparse
import sys
import mysql.connector
from mysql.connector import errorcode
from contextlib import closing
import validate
#import thomas_show
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
    parser = argparse.ArgumentParser(description="Deactivate entries in the user database. Use [positional argument -h] for more help.")
    # store which subparser was used in args.subcommand
    subparsers = parser.add_subparsers(dest="subcommand")

    # the arguments for subcommand 'user'
    userparser = subparsers.add_parser("user", help="Deactivate a user account - NOT YET FUNCTIONAL")
    userparser.add_argument("-u", "--user", dest="username", help="Username of user", action=ValidateUser)
    userparser.add_argument("--force", help="Force user deactivation without project confirmations (use with caution)", action='store_true')
    userparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    userparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')

    # the arguments for subcommand 'project'
    projectparser = subparsers.add_parser("project", help="Deactivate an entire project - NOT YET FUNCTIONAL")
    projectparser.add_argument("-p", "--project", dest="project", help="The existing project ID", required=True)
    projectparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    projectparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')

    # the arguments for subcommand 'projectuser'
    projectuserparser = subparsers.add_parser("projectuser", help="Deactivate this user's membership in this project")
    projectuserparser.add_argument("-u", "--user", dest="username", help="An existing username", required=True, action=ValidateUser)
    projectuserparser.add_argument("-p", "--project", dest="project", help="An existing project ID", required=True)
    parser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    projectuserparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')

    # the arguments for subcommand 'poc'
    #pocparser = subparsers.add_parser("poc", help="Deactivate this Point of Contact (only RC Support)")
    #pocparser.add_argument("-p", "--poc_id", dest="poc_id", help="Unique PoC ID, in form N(ame)N(ame)_instituteID", required=True)
    #pocparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    #pocparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')

    # the arguments for subcommand 'institute'
    #instituteparser = subparsers.add_parser("institute", help="Deactivate an entire institute/consortium (only RC Support)")
    #instituteparser.add_argument("-i", "--id", dest="inst_ID", help="Unique institute ID, eg QMUL, Imperial, Soton", required=True)
    #instituteparser.add_argument("--verbose", help="Show SQL queries that are being submitted", action='store_true')
    #instituteparser.add_argument("--debug", help="Show SQL query submitted without committing the change", action='store_true')

    # Show the usage if no arguments are supplied
    if len(argv) < 1:
        parser.print_usage()
        exit(1)

    # return the arguments
    # contains only the attributes for the main parser and the subparser that was used
    return parser.parse_args(argv)
# end getargs

# send an email to RC-Support notifying full account deactivation needed,
# unless debugging in which case just print it.
#def contact_rc_support(args, request_id):
#
#    body = (args.cluster.capitalize() + """ user deactivation request id """ + str(request_id) + """ has been received.
#
#Please run '""" + args.cluster + """-show requests' on a """ + args.cluster.capitalize() + """ login node to see pending requests.
#Requests can then be carried out by running '""" + args.cluster + """-deactivate request id1 [id2 id3 ...]'
#
#""")
#
#    msg = MIMEText(body)
#    msg["From"] = "rc-support@ucl.ac.uk"
#    msg["To"] = "rc-support@ucl.ac.uk"
#    msg["Subject"] = args.cluster.capitalize() + " deactivation request"
#    if (args.debug):
#        print("")
#        print("Email that would be sent:")
#        print(msg)
#    else:
#        p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE, universal_newlines=True)
#        p.communicate(msg.as_string())
#        print("RC Support has been notified to deactivate this account.")
# end contact_rc_support

# everything needed to create an account deactivation request
def deactivate_user_request(cursor, args, args_dict):
    # first, get user's active project memberships
    cursor.execute(thomas_queries.projectinfo(), args_dict)
    debug_cursor(cursor, args)
    results = cursor.fetchall()
    if (args.debug):
        print("Active projects found:")
        thomas_utils.tableprint_dict(results)
    if not args.force:
        # if they have any active, prompt (may have access via another inst)
        for row in results:
            answer = thomas_utils.are_you_sure("User has active membership in project " + row['project'] + " - deactivate it?", False)
            # they said no, exit
            if not answer:
                print("Active project membership being kept: user will not be deactivated.")
                exit(0)
    # deactivate all user's active memberships
    cursor.execute(thomas_queries.deactivatemembership(), args_dict)
    debug_cursor(cursor, args)

    # status in requests is pending until the full deactivation is done by us
    args_dict['status'] = "pending"
    
    # set user status to deactivated (can't run jobs but doesn't affect login)
    cursor.execute(thomas_queries.deactivateuser(), args_dict)
    debug_cursor(cursor, args)
    # get the deletion requestor and add to dictionary
    #cursor.execute(run_poc_email(), args_dict)
    #poc_email = cursor.fetchall()[0][0]
    #args_dict['poc_email'] = poc_email
    # add the account deactivation request to the database
    cursor.execute(run_deactivaterequest(), args_dict)
    debug_cursor(cursor, args)
# end deactivate_user_request


# Stubs for functions called elsewhere but not yet implemented
def run_deactivaterequest(*args):
    raise NotImplementedError

def run_poc(*args):
    raise NotImplementedError

def run_institute(*args):
    raise NotImplementedError


def debug_cursor(cursor, args):
    if (args.verbose or args.debug):
        print(cursor.statement)

# Put main in a function so it is importable.
def main(argv):

    # get the name of this cluster
    nodename = thomas_utils.getnodename()

# Doesn't appear to be an MMM cluster, prompt whether you really want to do this
    if not ("thomas" in nodename or "michael" in nodename or "young" in nodename):
        answer = thomas_utils.are_you_sure("Current hostname does not appear to be on Thomas or Michael or Young ("+nodename+")\n Do you want to continue?", False)
        # they said no, exit
        if not answer:
            exit(1)

    # get all the parsed args
    try:
        args = getargs(argv)
        # add cluster name to args
        args.cluster = thomas_utils.getcluster(nodename)
        # make a dictionary from args to make string substitutions doable by key name
        args_dict = vars(args)
    except ValueError as err:
        print(err, file=sys.stderr)
        exit(1)

    # Check that the user running the add command is a member of ccsprcop or lgmmmpoc or ag-archpc-mmm-poc-tools
    if not validate.user_has_privs():
        print("You need to be a member of the lgmmmpoc or ag-archpc-mmm-poc-tools or ccsprcop groups to run the deactivate commands. Exiting.", file=sys.stderr)
        exit(1)

    # get the MMM db to connect to
    db = thomas_utils.getdb(nodename)

    # connect to MySQL database with write access.
    # (.thomas.cnf has readonly connection details as the default option group)

    try:
        #conn = mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), option_groups='thomas_update', database=db)
        #cursor = conn.cursor()
        # make sure we close the connection wherever we exit from
        with closing(mysql.connector.connect(option_files=os.path.expanduser('~/.thomas.cnf'), option_groups='thomas_update', database=db)) as conn, closing(conn.cursor()) as cursor:

            if (args.verbose or args.debug):
                print("")
                print(">>>> Queries being sent:")

            # cursor.execute takes a querystring and a dictionary or tuple
            if (args.subcommand == "user"):
                #deactivate_user_request(cursor, args, args_dict)
                #print(args.username + "'s membership of " + args.project + " has been deactivated.")
                print("User deactivation functionality is not available yet - please email rc-support@ucl.ac.uk")
            elif (args.subcommand == "projectuser"):
                cursor.execute(thomas_queries.deactivateprojectuser(), args_dict)
                print(args.username + "'s membership of " + args.project + " is being deactivated.")
                debug_cursor(cursor, args)
            elif (args.subcommand == "project"):
                #cursor.execute(run_project(), args_dict)
                #debug_cursor(cursor, args)
                print("Whole project deactivation is not available yet. User membership in projects can be deactivated with the projectuser option.")
            elif (args.subcommand == "poc"):
                cursor.execute(run_poc(args.surname, args.username), args_dict)
                debug_cursor(cursor, args)
            elif (args.subcommand == "institute"):
                cursor.execute(run_institute(), args_dict)
                debug_cursor(cursor, args)

            # commit the change to the database unless we are debugging
            if (not args.debug):
                if (args.verbose):
                    print("")
                    print("Committing database change")
                    print("")
                conn.commit()

            # Databases are updated, now email rc-support unless nosupportemail is set
            #if (args.subcommand == "user" and args.nosupportemail == False):
                # get the last id added (which is from the requests table)
                # this has to be run after the commit
                #last_id = cursor.lastrowid
                #contact_rc_support(args, last_id)

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

# When not imported, use the normal global arguments
if __name__ == "__main__":
    main(sys.argv[1:])

