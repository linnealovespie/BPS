# Parent company search


## Overall Steps
1. Start with a company name. --> Taking addresses from the OSE dataset and looking up the tax parcel information. This contains a company name that owns said building. 
2. Find that company's official name in CCFS. --> Look up the company name from step 1 in the corproations and charities filing system. Sometimes we find an exact match, and sometimes there are a list of potential matches to sift through. 
3. Collect the principals/governors names from that company. 
4. Collect all the businesses with those same governors. --> When we look up a governor in the database, it will return a bunch of businesses in Washington state, some we may not care about. We filter these search results to only consider companies we care about. 
5. Human review to check which companies are connected based on number of overlapping governor, ID number, address, name, etc.
6. Profit

## An overview of the files in here: 

- exact_matches_*.csv (step 2): when looking up a company's name in CCFS, there was an exact match in the database. 
- potential_matches_*.csv (step 2): when looking up a company's name in CCFS, sometimes there aren't exact matches. Humans went in and hand-labelled when they think a search result matches the original company name. 
- all_matches_principals (step 3): all of the principals for all of the companies we care about. This is what we will iterate through to find potential matches. 
- all_matches (step 4): the compilation of all exact_matches and potential_matches into one file. Useful in step 4 because these are the only results we care about when looking up a particular governor. 
- companies_and_potential_matches (step 5): the file that needs human verification to see if, based on overlapping governors, if two companies are likely owned by the same "root" company. The formatting of this file is as such: 

    - SearchTerm: Original owner name from the 2020 building emissions dataset
    - BusinessName: The business name in the CCFS database that we have matched to the SearchTerm
    - PotentialRelatedCompany: A company that may be related to the company in the BusinessName field. If this field is the same as BusinessName, the row represents the "parent" or "hub" company that we are trying to match companies to
    - UBINumber: ID number
    - BusinessId: ID number
    - Address: Address of the PotentialRelatedCompany
    - Status: If the company is active/closed, etc.
    - Principals: A comma separated, alphabetized list of the PotenitalRelatedCompany's principals
    - isMatch: Your best guess about whether or not the PotentialRelatedCompany is connected to the BusinessName
    -notes: any useful notes about the company or explaining the isMatch value
