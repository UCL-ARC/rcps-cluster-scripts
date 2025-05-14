#!/usr/bin/env python3

import sys
import argparse
#import csv
import pandas

def getargs(argv):
    parser = argparse.ArgumentParser(description="Show allocation usage in given period.")
    parser.add_argument("--input", help="Gold allocations from stdin, input formed from glsalloc --raw", action='store_true')
    parser.add_argument("-i", "--institute", dest="institute", help="Show Gold total usage for this institute")
    parser.add_argument("-d", "--date", dest="date", help="Filter by start date of allocation period, in format yyyy-mm-dd")
    parser.add_argument("--csv", dest="csvfile", help="Write out CSV to this file in this location")
    parser.add_argument("--verbose", help="", action='store_true')
    parser.add_argument("--debug", help="", action='store_true')

    # Show the usage if no arguments are supplied
    if len(argv) < 1:
        parser.print_usage()
        exit(1)

    # return the arguments
    # contains only the attributes for the main parser and the subparser that was used
    return parser.parse_args(argv)
# end getargs


# Put main in a function so it is importable.
def main(argv):

    try:
        args = getargs(argv)
        # make a dictionary from args to make string substitutions doable by key name
        #args_dict = vars(args)
    except ValueError as err:
        print(err)
        exit(1)

    # Update Gold allocations from pipe-separated stdin input
    # Id|Account|Projects|StartTime|EndTime|Amount|Deposited|Description

    if args.input:
        dataframe = pandas.read_csv(sys.stdin, sep='|')
        # filter out the lines where StartTime is infinite
        dataframe = dataframe[dataframe.StartTime != "-infinity"]

        # filter by date
        if args.date is not None:
            dataframe = dataframe[dataframe.StartTime == args.date]
            # check we got any results for that date
            if dataframe.empty:
                print("No results found for start date " + args.date)
                exit(0)

        # add an institute column. We only want the first item in the split
        dataframe['Institute'] = dataframe['Projects'].str.split('_', 1).str[0]

        # filter by institute
        if args.institute is not None:
            # select all lines where institute matches
            dataframe = dataframe[dataframe.Institute == args.institute]
            # check we got any results for that institute
            if dataframe.empty:
                print("No results found for institute " + args.institute)
                exit(0)

        # filter out _allocation projects and everything else separately
        allocs = dataframe[dataframe.Projects.str.contains("_allocation")]
        projects = dataframe[~dataframe.Projects.str.contains("_allocation")]

        # We want this output:
        # StartTime  EndTime  Institute  Deposited  Unallocated  Allocated & Unused  Used  % Used
        projects = projects.rename(columns={'Amount':'Allocated & Unused'})
        allocs = allocs.rename(columns={'Amount':'Unallocated'})
        # sum the unused time for each institute in this period
        unused = projects.groupby(['StartTime','Institute'])['Allocated & Unused'].sum().reset_index()
        # merge the columns we want from allocs and unused
        # need a left outer join to keep allocs with no subprojects
        result = allocs[['StartTime', 'EndTime', 'Institute', 'Deposited', 'Unallocated']].merge(unused, on=['StartTime', 'Institute'], how='left')
        # replace NaN with 0
        result['Allocated & Unused'] = result['Allocated & Unused'].fillna(0)
        result['Used'] = result['Deposited'] - result['Unallocated'] - result['Allocated & Unused']
        result['% Used'] = result['Used']/result['Deposited']*100

        # write out as csv, leave off the row indices
        if args.csvfile is not None:
           result.to_csv(args.csvfile, index=False)
        else:
            # set display format of floats to 2dp and output all rows
            pandas.options.display.float_format = '{:.2f}'.format
            pandas.options.display.max_rows = None
            print(result)

    else:
        print("No input was specified.")

# end main

# When not imported, use the normal global arguments
if __name__ == "__main__":
    main(sys.argv[1:])

