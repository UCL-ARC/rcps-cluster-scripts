# mysql-connector queries for the Thomas database
# In most cases the values are inserted by cursor.execute(query, dict)
# from the given dictionary using that key name 
# eg. %(inst_ID)s will be provided args.dict['inst_ID']

################################################
#                                              #
# Queries that add new entries to the database #
#                                              #
################################################

# add a new user
def adduser(surname):
    query = ("""INSERT INTO users SET username=%(username)s, givenname=%(given_name)s, 
                 email=%(email)s, ssh_key=%(ssh_key)s, status=%(status)s, creation_date=now()""")
    if (surname is not None):
        query += ", surname=%(surname)s"
    return query

# add a new project-user relationship
def addprojectuser():
    query = ("""INSERT INTO projectusers SET username=%(username)s, 
                 project=%(project_ID)s, poc_id=%(poc_id)s, status=%(status)s, creation_date=now()""")
    return query

# add a new project
def addproject():
    query = ("""INSERT INTO projects SET project=%(project_ID)s, 
                 institute_id=%(inst_ID)s, creation_date=now()""")
    return query

# add a new point of contact
def addpoc(surname, username):
    query = ("""INSERT INTO pointofcontact SET poc_id=%(poc_id)s, 
                 poc_givenname=%(given_name)s, poc_email=%(email)s,  
                 institute=%(inst_ID)s, status=%(status)s, creation_date=now()""")
    if (surname is not None):
        query += ", poc_surname=%(surname)s"
    if (username is not None):
        query += ", username=%(username)s"
    return query

# add a new institute
def addinstitute():
    query = ("""INSERT INTO institutes SET inst_id=%(inst_ID)s, name=%(institute)s, 
                 creation_date=now()""")
    return query

# add a new account request
def addrequest():
    query = ("""INSERT INTO requests SET username=%(username)s, email=%(email)s, 
                 ssh_key=%(ssh_key)s, poc_cc_email=%(poc_email)s, cluster=%(cluster)s, 
                 creation_date=now()""")
    return query

###############################################
#                                             #
# Queries that update entries in the database #
#                                             #
###############################################

# update the status of a request
def updaterequest():
    query = ("""UPDATE requests SET isdone='1', approver=%s 
                WHERE id=%s""")
    return query

# activate a user
def activateuser():
    query = ("""UPDATE users SET status='active'
                WHERE username=%s""")
    return query

# activate a projectuser
def activateprojectuser():
    query = ("""UPDATE projectusers SET status='active'
                WHERE username=%(username)s AND project=%(project)s""")
    return query

def activatependingprojectuser():
    query = ("""UPDATE projectusers SET status='active'
                WHERE username=%s AND status='pending'""")
    return query

# deactivate this user
def deactivateuser():
    query = ("""UPDATE users SET status='deactivated'
                WHERE username=%s""")
    return query

# deactivate this projectuser
def deactivateprojectuser():
    query = ("""UPDATE projectusers SET status='deactivated'
                WHERE username=%(username)s AND project=%(project)s""")
    return query

# deactivate all project memberships for this user
def deactivatememberships():
    query = ("""UPDATE projectusers SET status='deactivated'
                WHERE username=%(username)s""")
    return query

# deactivate a whole project
def deactivateproject():
    query = ("""UPDATE projects SET status='deactivated'
                WHERE project=%(project)s""")
    return query

# deactivate all membership in this project
def deactivateallprojectusers():
    query = ("""UPDATE projectusers SET status='deactivated'
                WHERE project=%(project)s""")
    return query

# update SAFE ticket status in our DB
def updatesafestatus():
    query = ("""UPDATE safetickets SET status=%(status)s
                WHERE id=%(id)s""")
    return query

######################################################
#                                                    #
# Queries that insert/update entries in the database #
#                                                    #
######################################################

# Insert an open SAFE ticket or update it if it already exists.
# id is unique.
def refreshsafetickets():
    fields = ("""type=%(type)s, status=%(status)s, startdate=%(startdate)s, enddate=%(enddate)s, machine=%(machine)s, project=%(project)s, account_name=%(account_name)s, firstname=%(firstname)s, lastname=%(lastname)s, email=%(email)s, publickey=%(publickey)s, poc_firstname=%(poc_firstname)s, poc_lastname=%(poc_lastname)s, poc_email=%(poc_email)s, source_account_id=%(source_account_id)s, source_allocation=%(source_allocation)s, gold_amount=%(gold_amount)s, extratext=%(extratext)s""")
    query = ("""INSERT INTO safetickets SET id=%(id)s, """ + fields + """, creation_date=now()
                ON DUPLICATE KEY UPDATE """ + fields)
    return query

###################################################
#                                                 #
# Queries that read information from the database #
#                                                 #
###################################################

# Get user info (not ssh key as it is huge)
def userinfo():
    query = ("""SELECT username, givenname, surname, email, status, creation_date, modification_date 
                FROM users WHERE username=%(user)s""")
    return query

# Get ssh key on file
def sshinfo():
    query = ("""SELECT ssh_key FROM users WHERE username=%(user)s""")
    return query

# Get all of user's projects and related points of contact
def projectinfo():
    query = ("""SELECT project, poc_id, status, creation_date, modification_date 
                FROM projectusers WHERE username=%(user)s""")
    return query

# Get user's active projects
def activeprojectinfo():
    query = ("""SELECT project 
                FROM projectusers WHERE username=%(user)s AND status='active'""")
    return query

# Get all points of contact and their username if they have one.
def contactsinfo():
    query = ("""SELECT poc_id, poc_givenname, poc_surname, poc_email, institute, username 
                FROM pointofcontact""")
    return query

# Temporary: not all dbs have 'status' yet
def contactstatusinfo():
    query = ("""SELECT poc_id, poc_givenname, poc_surname, poc_email, institute, username, status 
                FROM pointofcontact""")
    return query

# Get all institutes
def instituteinfo():
    query = ("""SELECT inst_id, name FROM institutes""")
    return query

# Get all existing users (username, names, email, dates but not ssh keys)
def alluserinfo():
    query = ("""SELECT username, givenname, surname, email, status, creation_date, modification_date 
                FROM users""")
    return query

# Get the n latest users (not ssh keys). Default n provided by argparser.
def recentinfo():
    query = ("""SELECT username, givenname, surname, email, status, creation_date, modification_date 
                FROM users ORDER BY creation_date DESC LIMIT %(n)s""")
    return query

# Get the most recent mmm username used, across either db
def lastmmm():
    query = ("""SELECT username FROM young.users WHERE username LIKE 'mmm%' 
                UNION ALL 
                SELECT username FROM thomas.users WHERE username LIKE 'mmm%' 
                ORDER BY username DESC limit 1""")
    return query

# Get all users in this project/inst/PoC combo
# Need to use LIKE so can match all by default with % when an option is not specified
def projectcombo():
    query = ("""SELECT users.username, givenname, surname, email, projectusers.project, 
                    poc_id, institute_id FROM projectusers 
                  INNER JOIN users ON projectusers.username=users.username 
                  INNER JOIN projects ON projectusers.project=projects.project 
                WHERE projectusers.project LIKE %(project)s 
                  AND institute_id LIKE %(inst_ID)s 
                  AND poc_id LIKE %(poc_ID)s""")
    return query

# Search for users who match these criteria
# Allowing partial matches when %s is %username%.
# The default in that case is a blank, so ends up as %% which matches all
def whoisuser():
    query = ("""SELECT username, givenname, surname, email, status, creation_date, modification_date 
                FROM users 
                WHERE username LIKE %s AND email LIKE %s AND givenname LIKE %s 
                  AND surname LIKE %s""")
    return query
#cursor.execute(query, ("%" + args_dict["username"] + "%", "%" + args_dict["email"] + "%", "%" + args_dict["given_name"] + "%", "%" + args_dict["surname"] + "%"))

# Get all pending account requests for this cluster and also display the user's names. 
# ('is not true' will pick up any nulls, though there shouldn't be any).
# Ignore the open test request ids 7,8,10,11,778
def pendingrequests():
    query = ("""SELECT id, requests.username, users.givenname AS givenname, 
                  users.surname AS surname, requests.email, poc_cc_email, isdone, 
                  approver, cluster, requests.creation_date, requests.modification_date 
                FROM requests
                  INNER JOIN users ON requests.username = users.username
                WHERE isdone IS NOT TRUE
                  AND cluster=%(cluster)s
                  AND id NOT IN (7, 8, 10, 11, 778)""")
    return query

# For testing: get the open test request ids 7,8,10,11,778
def pendingtestrequests():
    query = ("""SELECT id, requests.username, users.givenname AS givenname, 
                  users.surname AS surname, requests.email, poc_cc_email, isdone, 
                  approver, cluster, requests.creation_date, requests.modification_date 
                FROM requests
                  INNER JOIN users ON requests.username = users.username
                WHERE isdone IS NOT TRUE
                  AND cluster=%(cluster)s
                  AND id IN (7, 8, 10, 11, 778)""")
    return query

# Get all existing requests and also display the user's names.
def allrequests():
    query = ("""SELECT id, requests.username, users.givenname AS givenname, 
                  users.surname AS surname, requests.email, poc_cc_email, isdone, 
                  approver, cluster, requests.creation_date, requests.modification_date 
                FROM requests
                  INNER JOIN users ON requests.username = users.username""")
    return query

# Get the n most recent requests, in any state. Default n provided by argparser.
def recentrequests():
    query = ("""SELECT id, requests.username, users.givenname AS givenname, 
                  users.surname AS surname, requests.email, poc_cc_email, isdone, 
                  approver, cluster, requests.creation_date, requests.modification_date 
                FROM requests
                  INNER JOIN users ON requests.username = users.username
                ORDER BY creation_date DESC LIMIT %(n)s""")
    return query

# Get the requests matching the given id(s)
# The format string adds the correct number of %s for the number of ids
def getrequestbyid(num_ids):
    format_strings = ','.join(['%s'] * num_ids)
    query = ("""SELECT id, username, email, ssh_key, poc_cc_email, isdone, approver, cluster 
                FROM requests 
                WHERE id IN (%s)""" % format_strings)
    return query

# Find duplicate users by key: mostly email or username
def findduplicate(key_string):
    query = ("""SELECT username, givenname, surname, email, creation_date, modification_date 
                FROM users 
                WHERE """ + key_string +"""=%(""" + key_string + """)s""")
    return query

# Get all points of contact with matching email
def findpocbyemail():
    query = ("""SELECT poc_givenname, poc_surname, poc_email
                FROM pointofcontact 
                WHERE poc_email=%(poc_email)s""")
    return query

def findpocbyemailandinst():
    query = ("""SELECT poc_givenname, poc_surname, poc_email
                FROM pointofcontact 
                WHERE poc_email=%(poc_email)s
                  AND institute=%(institute)s""")
    return query

def findpocbylastname():
    query = ("""SELECT poc_givenname, poc_surname, poc_email
                FROM pointofcontact 
                WHERE poc_surname=%(poc_surname)s""")
    return query

def findpocbyusername():
    query = ("""SELECT poc_id,  poc_givenname, poc_surname, poc_email
                FROM pointofcontact 
                WHERE username=%(username)s""")
    return query

# Get all open tickets for printing (not including the ssh keys)
def showpendingtickets():
    query = ("""SELECT id, type, status, account_name, machine, project, firstname, lastname, 
                  email, poc_firstname, poc_lastname, poc_email, source_account_id,
                  source_allocation, gold_amount, extratext, startdate, enddate
                FROM safetickets 
                WHERE status='Pending'""")
    return query

# Get the type of a SAFE ticket
def safetickettype():
    query = ("""SELECT type 
                FROM safetickets 
                WHERE id=%(id)s""")
    return query

# Get a SAFE ticket by ID
def getsafeticket():
    query = ("""SELECT id, type, status, account_name, machine, project, firstname, lastname, 
                  email, publickey, poc_firstname, poc_lastname, poc_email, source_account_id, 
                  source_allocation, gold_amount, extratext, startdate, enddate
                FROM safetickets 
                WHERE id=%(id)s""")
    return query

# Get all open 'Add to budget' tickets belonging to this user
def getusersbudgettickets():
    query = ("""SELECT id, type, status, account_name, machine, project, firstname, lastname, 
                  email, publickey, poc_firstname, poc_lastname, poc_email, startdate, enddate
                FROM safetickets 
                WHERE status='Pending'
                  AND type='Add to budget'
                  AND account_name=%(account_name)s""")
    return query


