# This module provides classes and procedures for converting JSON SAFE tickets
# into Python classes.

# Many fields are optional depending on the type of ticket, so they are 
# initialised to empty when they do not exist.

# JSONDataToTickets(yourjsondata) parses JSON into a list of Python objects.

# Also includes fairly dodgy __str__ methods for testing purposes.

# Owain Kenway

# For reasons the request is enclosed in a Sysadmin object.
class SysAdmin:

    known_keys = ["Id", "Type", "Status", "StartDate", "EndDate", "Machine", "Handler", "Approver", "Person", "ProjectGroup", "Project", "Account", "ExtraText", "GoldTransfer"]

    def __init__(self, SysAdminDict):
        for a in SysAdminDict.keys():
            if a not in self.known_keys:
                print("Warning [SysAdmin]: Detected unknown key: " + a + ": " + str(SysAdminDict[a]))
        self.Id=SysAdminDict["Id"]
        self.Type=SysAdminDict["Type"]
        self.Status=SysAdminDict["Status"]
        self.StartDate=SysAdminDict["StartDate"]
        self.EndDate=SysAdminDict["EndDate"]
        self.Machine=SysAdminDict["Machine"]
        self.HandlerName=SysAdminDict["Handler"]["Name"]
        self.HandlerEmail=SysAdminDict["Handler"]["Email"]
        # Approver is an instance of Person
        if "Approver" in SysAdminDict.keys():
            self.Approver=Person(SysAdminDict["Approver"])
        else:
            self.Approver=Person()
        if "Person" in SysAdminDict.keys():
            self.Person=Person(SysAdminDict["Person"])
        else:
            self.Person=Person()
        if "ProjectGroup" in SysAdminDict.keys():
            self.ProjectGroup=ProjectGroup(SysAdminDict["ProjectGroup"])
        else:
            self.ProjectGroup=ProjectGroup()
        if "Project" in SysAdminDict.keys():
            self.Project=Project(SysAdminDict["Project"])
        else:
            self.Project=Project()
        if "Account" in SysAdminDict.keys():
            self.Account=Account(SysAdminDict["Account"])            
        else:
            self.Account=Account()
        self.ExtraText=""
        if "ExtraText" in SysAdminDict.keys():
            self.ExtraText=SysAdminDict["ExtraText"]
        if "GoldTransfer" in SysAdminDict.keys():
            self.GoldTransfer=GoldTransfer(SysAdminDict["GoldTransfer"])
        else:
            self.GoldTransfer=GoldTransfer()

    def __str__(self):
        return "SysAdmin: " + ",\n".join([self.Id, 
                                        self.Type, 
                                        self.Status, 
                                        self.StartDate, 
                                        self.EndDate,
                                        self.HandlerName,
                                        self.HandlerEmail,
                                        str(self.Approver),
                                        str(self.Person),
                                        str(self.Project),
                                        str(self.ProjectGroup),
                                        str(self.Account),
                                        self.Machine,
                                        self.ExtraText,
                                        str(self.GoldTransfer)])

class Project:

    known_keys = ["Code", "Id", "Name", "Status", "ProjectClass", "FundingBody", "Machines", "TopGroup"]

    def __init__(self, ProjectDict=None):
        # Empty values are created if no dict is passed in.
        if ProjectDict is None:
            for a in self.known_keys:
                setattr(self, a, "")
        else:
            for a in ProjectDict.keys():
                if a not in self.known_keys:
                    print("Warning [Project]: Detected unknown key: " + a + ": " + str(ProjectDict[a]))
            # ternary: if a key is missing, set it to empty
            self.Code=ProjectDict["Code"] if "Code" in ProjectDict.keys() else ""
            self.Code=ProjectDict["Id"] if "Id" in ProjectDict.keys() else ""
            self.Name=ProjectDict["Name"] if "Name" in ProjectDict.keys() else ""
            self.Status=ProjectDict["Status"] if "Status" in ProjectDict.keys() else ""
            self.ProjectClass=ProjectDict["ProjectClass"] if "ProjectClass" in ProjectDict.keys() else ""
            self.FundingBody=ProjectDict["FundingBody"] if "FundingBody" in ProjectDict.keys() else ""
            self.Machines=str.split(ProjectDict["Machines"], ",") if "Machines" in ProjectDict.keys() else "" # Comma sep list
            self.TopGroup=ProjectGroup(ProjectDict["TopGroup"]) if "TopGroup" in ProjectDict.keys() else ""

    def __str__(self):
        return "Project: " + ",\n".join([self.Code,
                                        self.Id,
                                        self.Name,
                                        self.Status,
                                        self.ProjectClass,
                                        self.FundingBody,
                                        str(self.Machines),
                                        str(self.TopGroup)])

class ProjectGroup:

    known_keys = ["Code", "GroupID"]
 
    def __init__(self, ProjectGroupDict=None):
        # Empty values are created if no dict is passed in.
        if ProjectGroupDict is None:
            for a in self.known_keys:
                setattr(self, a, "")
        else:
            for a in ProjectGroupDict.keys():
                if a not in self.known_keys:
                    print("Warning [ProjectGroup]: Detected unknown key: " + a + ": " + str(ProjectGroupDict[a]))
            # ternary: if a key is missing, set it to empty
            self.Code=ProjectGroupDict["Code"] if "Code" in ProjectGroupDict.keys() else ""
            self.GroupID=ProjectGroupDict["GroupID"] if "GroupID" in ProjectGroupDict.keys() else ""

    def __str__(self):
        return "ProjectGroup: " + ",\n".join([self.Code,
                                            self.GroupID])

class GoldTransfer:
    known_keys = ["Amount", "SourceAllocation", "SourceAccountID"]

    def __init__(self, GoldDict=None):
        # Empty values are created if no dict is passed in.
        if GoldDict is None:
            for a in self.known_keys:
                setattr(self, a, "")
        else:
            for a in GoldDict.keys():
                if a not in self.known_keys:
                    print("Warning [GoldTransfer]: Detected unknown key: " + a + ": " + str(GoldDict[a]))
            # ternary: if a key is missing, set it to empty
            self.Amount=GoldDict["Amount"] if "Amount" in GoldDict.keys() else ""
            self.SourceAllocation=GoldDict["SourceAllocation"] if "SourceAllocation" in GoldDict.keys() else ""
            self.SourceAccountID=GoldDict["SourceAccountID"] if "SourceAccountID" in GoldDict.keys() else ""

    def __str__(self):
        return "GoldTransfer: " + ",\n".join([self.Amount,
                                        self.SourceAllocation,
                                        self.SourceAccountID])

class Account:

    known_keys = ["Name", "GID", "Groups", "Person", "UID", "Machines"]

    def __init__(self, AccountDict=None):
        # Empty values are created if no dict is passed in.
        if AccountDict is None:
            for a in ["Name", "GroupID", "Groups", "UserID", "Machines"]:
                setattr(self, a, "")
            self.Person=Person()
        else:
            for a in AccountDict.keys():
                if (a not in self.known_keys) and (not a.startswith("Group")):
                    print("Warning [Account]: Detected unknown key: " + a + ": " + str(AccountDict[a]))
            # ternary: if a key is missing, set it to empty
            self.Name=AccountDict["Name"] if "Name" in AccountDict.keys() else ""
            self.GroupID=AccountDict["GID"] if "GID" in AccountDict.keys() else ""
        
            # Need code for parsing group fmt
            self.Groups=[]
            for a in AccountDict.keys():
                if (a.startswith("Group") and a != "Groups"):
                    self.Groups.append(ProjectGroup(AccountDict[a])) 

            self.Person=Person(AccountDict["Person"]) if "Person" in AccountDict.keys() else Person()
            self.UserID=AccountDict["UID"] if "UID" in AccountDict.keys() else ""
            self.Machines=str.split(AccountDict["Machines"], ",") if "Machines" in AccountDict.keys() else ""

    def __str__(self):
        strGroups = "Groups: "
        for a in self.Groups:
            strGroups += str(a) + ",\n"

        return "Account: " + ",\n".join([self.Name,
                                        self.GroupID,
                                        str(self.Person),
                                        strGroups,
                                        self.UserID,
                                        str(self.Machines)])

class Person:

    known_keys = ["Name", "Email", "WebName", "UKAMF", "PublicKey", "NormalisedPublicKey", "HartreeName"]

    def __init__(self, PersonDict=None):
        # Empty values are created if no dict is passed in.
        if PersonDict is None:
            for a in ["Title", "FirstName", "LastName", "Email", "WebName", "UKAMF", "PublicKey", "NormalisedPublicKey", "HartreeName"]:
                setattr(self, a, "")
        else:
            for a in PersonDict.keys():
                if a not in self.known_keys:
                    print("Warning [Person]: Detected unknown key: " + a + ": " + str(PersonDict[a]))
            
            self.Title=PersonDict["Name"]["Title"]
            if self.Title is None:
                self.Title = ""
            self.FirstName=PersonDict["Name"]["Firstname"]
            self.LastName=PersonDict["Name"]["Lastname"]
            self.Email=PersonDict["Email"]
            self.WebName=PersonDict["WebName"] if "WebName" in PersonDict.keys() else ""
            self.WebName=PersonDict["UKAMF"] if "UKAMF" in PersonDict.keys() else ""
            self.PublicKey=PersonDict["PublicKey"] if "PublicKey" in PersonDict.keys() else ""
            self.NormalisedPublicKey=PersonDict["NormalisedPublicKey"] if "NormalisedPublicKey" in PersonDict.keys() else ""
            self.HartreeName=PersonDict["HartreeName"] if "HartreeName" in PersonDict.keys() else ""

    def __str__(self):
        return "Person: " + ",\n".join([
                                        self.Title,
                                        self.FirstName,
                                        self.LastName,
                                        self.Email,
                                        self.WebName,
                                        self.UKAMF,
                                        self.PublicKey,
                                        self.NormalisedPublicKey,
                                        self.HartreeName])

class AccountRequest:

    def __init__(self, SystemTicketDict):
        self.Ticket=SysAdmin(SystemTicketDict["SysAdmin"])

# Convert String to objects.
def JSONtoTickets(JSONData):
    import json
    from io import StringIO

    jsdata = json.load(StringIO(JSONData))

    return JSONDataToTickets(jsdata)

# Convert JSON data structure to a list of objects
def JSONDataToTickets(JSONData):
    Tickets = []
    if type(JSONData) is list:
        for a in JSONData:
            Tickets.append(AccountRequest(a))
    else:
        Tickets.append(AccountRequest(JSONData))
    return Tickets

# If this is run directly, process test.json in the current working directory 
# and print the output as a string.
if __name__=="__main__":
    import sys

    filename="test.json"

    if len(sys.argv) > 1:
	    filename=sys.argv[1]

    f = open(filename, 'r')
    jdata=f.read()
    ar=JSONtoTickets(jdata)
    f.close()
    for a in ar:
        print(str(a.Ticket))
    
    print("Number of tickets included: " + str(len(ar)))
