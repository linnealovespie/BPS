"""
    Utility functions for extracting owners. 
"""

import pandas as pd
import numpy as np
import requests
import json
import os
import re
import geopandas as gp
import urllib.parse

# Utils for finding principals

search_for_business_url = 'https://cfda.sos.wa.gov/api/BusinessSearch/GetBusinessSearchList'
principal_url = 'https://cfda.sos.wa.gov/api/BusinessSearch/GetAdvanceBusinessSearchList'

principal_headers = {
    'Accept-Language': 'en-US,en;q=0.8,es-AR;q=0.5,es;q=0.3',
    'Referer': 'https://ccfs.sos.wa.gov/',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8', # this might be an issue
    'Origin': 'https://ccfs.sos.wa.gov'
}


def get_business_details(business_id):
    """ Get business details from the Corporation and charities filing database. """
    url = 'https://cfda.sos.wa.gov/api/BusinessSearch/BusinessInformation?businessID={business_id}'.format(business_id=business_id)
    r = requests.get(url)
    return json.loads(r.text)


def extract_principals(business_res, business_id):
    """ Given a single JSON response for one business, return a dataframe for the given 
        business where each line represents a principal registered to that business. 
    """
    agent = business_res['Agent']['EntityName']
    rows = [[
        # name of company?
        business_id,
        agent,
        'Entity' if principal['TypeID'] == 'E' else 'Individual',
        principal['PrincipalID'],
         principal['Name'] if principal['TypeID'] == 'E' else principal['FirstName'] + ' ' + principal['LastName']
    ] for principal in business_res['PrincipalsList']]
    return pd.DataFrame(rows, columns=['BusinessId', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName'])

def get_companies_principals(business_names_df):
    '''
        Given a list of businesses as a dataframe, return a dataframe with all the businesses and a row for 
        each principal. Therefore if a compnay has multiple principals registered, there will be multiple lines
        for that company in the returned dataframe. 
    '''
    principals = pd.DataFrame([], columns=['BusinessId', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName'])
    for business in business_names_df['BusinessId']:
        business_res = get_business_details(business)
        principals = pd.concat([extract_principals(business_res, business), principals], ignore_index=True)
    
    merged_principals = pd.merge(business_names_df, principals, on='BusinessId', how='left')
    
    return merged_principals

def get_principal_data(principal_name, page_num):
        principal_name = urllib.parse.quote(principal_name)
        return 'Type=Principal&BusinessStatusID=0&SearchEntityName=&SearchType=&BusinessTypeID=0&AgentName=&PrincipalName={principal_name}&StartDateOfIncorporation=&EndDateOfIncorporation=&ExpirationDate=&IsSearch=true&IsShowAdvanceSearch=true&&&AgentAddress%5BIsAddressSame%5D=false&AgentAddress%5BIsValidAddress%5D=false&AgentAddress%5BisUserNonCommercialRegisteredAgent%5D=false&AgentAddress%5BIsInvalidState%5D=false&AgentAddress%5BbaseEntity%5D%5BFilerID%5D=0&AgentAddress%5BbaseEntity%5D%5BUserID%5D=0&AgentAddress%5BbaseEntity%5D%5BCreatedBy%5D=0&&AgentAddress%5BbaseEntity%5D%5BModifiedBy%5D=0&&AgentAddress%5BFullAddress%5D=%2C%20WA%2C%20USA&AgentAddress%5BID%5D=0&&&&AgentAddress%5BState%5D=WA&&AgentAddress%5BCountry%5D=USA&&&&&&&&PrincipalAddress%5BIsAddressSame%5D=false&PrincipalAddress%5BIsValidAddress%5D=false&PrincipalAddress%5BisUserNonCommercialRegisteredAgent%5D=false&PrincipalAddress%5BIsInvalidState%5D=false&PrincipalAddress%5BbaseEntity%5D%5BFilerID%5D=0&PrincipalAddress%5BbaseEntity%5D%5BUserID%5D=0&PrincipalAddress%5BbaseEntity%5D%5BCreatedBy%5D=0&&PrincipalAddress%5BbaseEntity%5D%5BModifiedBy%5D=0&&PrincipalAddress%5BFullAddress%5D=%2C%20WA%2C%20USA&PrincipalAddress%5BID%5D=0&&&&PrincipalAddress%5BState%5D=&&PrincipalAddress%5BCountry%5D=USA&&&&&&PageID={page_num}&PageCount=100'.format(principal_name=principal_name, page_num=page_num)

def get_principal_response(principal_name, page_num):
    data = get_principal_data(principal_name, page_num)
    r = requests.post(principal_url, data=data, headers=principal_headers)
    return json.loads(r.text)

def extract_principals_business(business_res, business_id, business_name):
    """
        Given a json of the business search result business_res and the business' id, 
        Create a dataframe of all the principals returned in business_res.
    """
    agent = business_res['Agent']['EntityName']
    rows = [[
        business_res['UBINumber'],
        business_id,
        business_name,
        agent,
        'Entity' if principal['TypeID'] == 'E' else 'Individual',
        principal['PrincipalID'],
        principal['Name'] if principal['TypeID'] == 'E' else principal['FirstName'] + ' ' + principal['LastName'],
        business_res['PrincipalOffice']['PrincipalStreetAddress']['FullAddress'],
        business_res["BusinessStatus"]
    ] for principal in business_res['PrincipalsList']]
    return pd.DataFrame(rows, columns=['UBINumber', 'BusinessId', 'BusinessName', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName', "Address", "Status"])

def get_all_principal_search_results(principal_name):
    n = 1
    res_length = 100
    search_results = []
    
    while res_length == 100:
        res = get_principal_response(principal_name, n)
        search_results += res
        n += 1
        res_length = len(res)
    
    return search_results

def get_all_companies_from_principal_dataframe(principal_match_list, principal_name):
    """ Returns every row in `principal_match_list` where the business has `principal_name` listed as a principal. """
    companies_with_same_principal = principal_match_list[principal_match_list['PrincipalName'] == principal_name].BusinessId.unique()
    return principal_match_list[principal_match_list["BusinessId"].isin(companies_with_same_principal)]

def get_all_companies_from_principal_lookup(principal_name):
    """
        [DEPRECATED] Looks up principal name in the CDFA database and returns all companies in the results as a dataframe. 
        This doesn't filter by region of interest (eg. companies in the results might not be relevant to our grouping exercise).
        To limit the lookup of companies by principal to the companies we care about see, get_all_companies_from_principal_dataframe
    """
    # should include company name, see below
    principals = pd.DataFrame([], columns=['UBINumber', 'BusinessId', 'BusinessName', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName'])

    try:
        search_results = get_all_principal_search_results(principal_name)
    except:
        print(f"couldn't get results for {principal_name}")
        return principals
    business_ids = [res['BusinessID'] for res in search_results]
    business_names = [res['BusinessName'] for res in search_results]
    ubi_nums = [res['UBINumber'] for res in search_results]
    
    for id, name in zip(business_ids, business_names):
        business_json = get_business_details(id)
        principals_df = extract_principals_business(business_json, id, name)
        
        if len(principals_df[principals_df['PrincipalName'] == principal_name]) > 0:
            principals = pd.concat([extract_principals_business(business_json, id, name), principals], ignore_index=True)
        # principals = principals[principals['BusinessId'].isin(all_matches['BusinessId'].values)]
    return principals


def group_companies_by_principals(principal_match_list, out_file_path):
    """
        Given a list of businesses with one line for each principal registered for that business, returns 
        a dataframe where companies are grouped by whether they share a principal. 
        
        principal_match_list is an output from previous steps, like the dataframe `all_matches_principals.csv`
    """
    print(f"Saving to {out_file_path}")
    columns=['SearchTerm', 'BusinessName', 'PotentialRelatedCompany', 'UBINumber', 'BusinessId', 'Address', 
             'Status', 'Agent', 'Principals', 'isMatch', 'notes']
    results = pd.DataFrame([], columns)
    for idx, row in principal_match_list.iterrows():
        possible_matching_companies_df = get_all_companies_from_principal_dataframe(principal_match_list, row['PrincipalName'])
        grouped = possible_matching_companies_df.groupby("BusinessName")
        for name, group in grouped:
            principals_list = group["PrincipalName"].tolist()
            principals_list.sort()
            poss_company = group.iloc[0]

            # # row['BusinessName']: the name we mapped to from SearchTerm
            # # poss_company['BusinessName]: PotentialRelatedCompany
            new_row = pd.Series(data=[row['SearchTerm'], 
                            row["BusinessName"], 
                            poss_company["BusinessName"],
                            poss_company['UBINumber'],
                            poss_company["BusinessId"],
                            poss_company["Address"],
                            poss_company["Status"],
                            poss_company["Agent"],
                            principals_list,
                            "", # isMatch
                            ""  # Notes
                            ], 
                        index = columns)
            results = pd.concat([new_row.to_frame().T, results], ignore_index=True).drop_duplicates(subset="UBINumber").dropna()
            # results = results[results['BusinessId'].isin(all_matches['BusinessId'])]
        if(idx % 25 == 0): 
            print(f"Processing row {idx} of principal_match_list, results is {len(results)}")
            results.to_csv(f"{out_file_path}.csv")
    return results