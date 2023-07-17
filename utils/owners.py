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

def get_business_search_payload(business_name, page_count, page_num):
    return {
        'Type': 'BusinessName',
        'SearchEntityName': business_name,
        'SearchType': 'BusinessName',
        'SortType': 'ASC',
        'SortBy': 'Entity Name',
        'SearchValue': business_name,
        'SearchCriteria': 'Contains',
        'IsSearch': 'true',
        'PageID': page_num,
        'PageCount': page_count,
    }

def get_business_details(business_id):
    """ Get business details from the Corporation and charities filing database. """
    url = 'https://cfda.sos.wa.gov/api/BusinessSearch/BusinessInformation?businessID={business_id}'.format(business_id=business_id)
    r = requests.get(url)
    return json.loads(r.text)


class LookupCompaniesHelper:
    def __init__(self, out_path: str):
        self.output_path = out_path # Absolute path to where the file will be saved

    def _get_empty_df(self):
        return pd.DataFrame([], columns = ['SearchTerm', 'BusinessName', 'UBINumber', 'BusinessId', 
                                           'Address', 'Status', 'address_match', 'ubi_match', 'id_match'])
    
    def _get_business_search_results(self, business_name, page_num):
        r = requests.post(search_for_business_url, get_business_search_payload(business_name, 100, page_num))
        try:
            result = json.loads(r.text)
        #return json.loads(r.text)
        except:
            result = {}
        return result

    def _extract_search_results(self, search_term, search_req_response):
        res_list = [[search_term, res['BusinessName'], res['UBINumber'], res['BusinessID'],
                    res['PrincipalOffice']['PrincipalStreetAddress']['FullAddress'], res["BusinessStatus"]] 
                    for res in search_req_response]
        res_df = pd.DataFrame(res_list, columns=['SearchTerm', 'BusinessName', 'UBINumber', 'BusinessId', 'Address', "Status"])
        # Basically keep a list of exact matches, and build a list of potential matches that we give to human verifiers
        exact_match = res_df.index[res_df['BusinessName'] == search_term].tolist()
        if exact_match:
            res_df = pd.concat([res_df.iloc[[exact_match[0]],:], res_df.drop(exact_match[0], axis=0)], axis=0)
        return res_df

    def _determine_search_matches(self, search_results_df):
        """
            Mark row as potential match: UBI number is a duplicate, or Address is the same
            df.duplicated just sees if that address is already in the dataframe, NOT that the serach term
            and result have the same address. Could add search terms as a subset for duplicated call
        """
        search_results_df['address_match'] = search_results_df.duplicated(subset=['Address'], keep=False) 
        search_results_df['ubi_match'] = search_results_df.duplicated(subset=['UBINumber'], keep=False)
        search_results_df['id_match'] = search_results_df.duplicated(subset=['BusinessId'], keep=False)

    def _get_all_company_name_match_search_results(self, owner_name):
        n = 1
        res_length = 100
        search_results = []
        
        while res_length == 100:
            res = self._get_business_search_results(owner_name, n)
            search_results += (res)
            n += 1
            res_length = len(res)
        
        return search_results

    def _get_potential_company_name_matches(self, owner_name):
        all_search_results = self._get_all_company_name_match_search_results(owner_name)
        extracted_results = self._extract_search_results(owner_name, all_search_results)
        self._determine_search_matches(extracted_results)
        return extracted_results

    def _separate_search_results(self, results):
        """
            utils to separate search results into exact match, potential match (where no exact match was found), 
            and additional matches (extra matches if there was an exact match and additional matches)
        """
        def is_exact_match(row):
            """ Extract exact matches, including some regex magic. """
            search = row["SearchTerm"]
            result = row["BusinessName"]

            # examples: LLC, LLP, L L C, L.L.C., L.L.C. L.L.P., L.L.P, LLC.
            # Limited Partnership, Limited liability company
            p = re.compile("L[\s.]?L[\s,.]?[PC][.]" ,flags=re.IGNORECASE)
            result=result.replace(",", "")
            result= re.sub(p, "LLC", result)
            result=result.replace("LIMITED LIABILITY COMPANY", "LLC") 
            result=result.replace("LIMITED PARTNERSHIP", "LLC") 

            search=search.replace(",", "")
            search=re.sub(p, "LLC", search)
            search=search.replace("LIMITED PARTNERSHIP", "LLC") 
            search=search.replace("LIMITED LIABILITY COMPANY", "LLC") 

            return search == result
        
        exact_matches = self._get_empty_df()
        exact_matches.columns
        potential_matches = self._get_empty_df()
        additional_matches = self._get_empty_df()
        
        exact_match = results[results.apply(lambda row: is_exact_match(row), axis=1)]
        if len(exact_match) > 0:
            exact_matches = pd.concat([exact_matches, exact_match], ignore_index=True)
            additional_matches = pd.concat([additional_matches, results[results['SearchTerm'] != results['BusinessName']]], ignore_index=True)
        else:
            potential_matches = pd.concat([potential_matches, results], ignore_index=True)
        
        return exact_matches, potential_matches, additional_matches

    def get_company_list_name_matches(self, owner_list: list):
        """
            Given a list of owners `owner_list`, returns exact, potential, and additional matches. 
            owner_list: a list of owner names that will be searched in the CCFS database for matches.
            Exact_matches: when search term exactly matches a result in CCFS database. 
            Potential_matches: when search term doesn't exactly match, there needs to be some human verification here to determine. 
            Additional_matches: extraneous matches in case potential_matches didn't yield enough results. 
        """
        exact_matches = self._get_empty_df()
        potential_matches = self._get_empty_df()
        additional_matches = self._get_empty_df()
        
        for owner in owner_list:
            matches = self._get_potential_company_name_matches(owner)
            temp_exact, temp_potential, temp_add = self._separate_search_results(matches)
            exact_matches = pd.concat([temp_exact, exact_matches], ignore_index=True)
            potential_matches = pd.concat([temp_potential, potential_matches], ignore_index=True)
            additional_matches = pd.concat([temp_add, additional_matches], ignore_index=True)
        return exact_matches, potential_matches, additional_matches
    

    def get_company_matches_and_export(self, owner_list: list, x: int):
        """
            Given a list of owners `owner_list` and batch number `x`, get all matches and save to exact, potential, and additional
            match CSV's in the folder determined by `output_path`
        """
        print(f"Saving output files to {self.output_path}")
        exact_matches, potential_matches, additional_matches = self.get_company_list_name_matches(owner_list)
        
        exact_matches.to_csv(f'{self.output_path}/exact_matches_{x}.csv')
        potential_matches.to_csv(f'{self.output_path}/potential_matches_{x}.csv')
        additional_matches.to_csv(f'{self.output_path}/additional_matches_{x}.csv')

class GroupCompaniesHelper:
    def __init__(self, out_path: str, out_name: str):
        self.output_path = out_path # The path to the output file to save the output file
        self.output_name = out_name # The full name of the output file, eg. "companies_and_matches.csv"

    def _extract_principals(self, business_res, business_id):
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

    def _get_principal_data(self, principal_name, page_num):
            principal_name = urllib.parse.quote(principal_name)
            return 'Type=Principal&BusinessStatusID=0&SearchEntityName=&SearchType=&BusinessTypeID=0&AgentName=&PrincipalName={principal_name}&StartDateOfIncorporation=&EndDateOfIncorporation=&ExpirationDate=&IsSearch=true&IsShowAdvanceSearch=true&&&AgentAddress%5BIsAddressSame%5D=false&AgentAddress%5BIsValidAddress%5D=false&AgentAddress%5BisUserNonCommercialRegisteredAgent%5D=false&AgentAddress%5BIsInvalidState%5D=false&AgentAddress%5BbaseEntity%5D%5BFilerID%5D=0&AgentAddress%5BbaseEntity%5D%5BUserID%5D=0&AgentAddress%5BbaseEntity%5D%5BCreatedBy%5D=0&&AgentAddress%5BbaseEntity%5D%5BModifiedBy%5D=0&&AgentAddress%5BFullAddress%5D=%2C%20WA%2C%20USA&AgentAddress%5BID%5D=0&&&&AgentAddress%5BState%5D=WA&&AgentAddress%5BCountry%5D=USA&&&&&&&&PrincipalAddress%5BIsAddressSame%5D=false&PrincipalAddress%5BIsValidAddress%5D=false&PrincipalAddress%5BisUserNonCommercialRegisteredAgent%5D=false&PrincipalAddress%5BIsInvalidState%5D=false&PrincipalAddress%5BbaseEntity%5D%5BFilerID%5D=0&PrincipalAddress%5BbaseEntity%5D%5BUserID%5D=0&PrincipalAddress%5BbaseEntity%5D%5BCreatedBy%5D=0&&PrincipalAddress%5BbaseEntity%5D%5BModifiedBy%5D=0&&PrincipalAddress%5BFullAddress%5D=%2C%20WA%2C%20USA&PrincipalAddress%5BID%5D=0&&&&PrincipalAddress%5BState%5D=&&PrincipalAddress%5BCountry%5D=USA&&&&&&PageID={page_num}&PageCount=100'.format(principal_name=principal_name, page_num=page_num)

    def _get_principal_response(self, principal_name, page_num):
        data = self._get_principal_data(principal_name, page_num)
        r = requests.post(principal_url, data=data, headers=principal_headers)
        return json.loads(r.text)

    def _extract_principals_business(self, business_res, business_id, business_name):
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

    def _get_all_principal_search_results(self, principal_name):
        n = 1
        res_length = 100
        search_results = []
        
        while res_length == 100:
            res = self._get_principal_response(principal_name, n)
            search_results += res
            n += 1
            res_length = len(res)
        
        return search_results

    def _get_all_companies_from_principal_dataframe(self, principal_match_list, principal_name):
        """ Returns every row in `principal_match_list` where the business has `principal_name` listed as a principal. """
        companies_with_same_principal = principal_match_list[principal_match_list['PrincipalName'] == principal_name].BusinessId.unique()
        return principal_match_list[principal_match_list["BusinessId"].isin(companies_with_same_principal)]

    def _get_all_companies_from_principal_lookup(self, principal_name):
        """
            [DEPRECATED] Looks up principal name in the CDFA database and returns all companies in the results as a dataframe. 
            This doesn't filter by region of interest (eg. companies in the results might not be relevant to our grouping exercise).
            To limit the lookup of companies by principal to the companies we care about see, get_all_companies_from_principal_dataframe
        """
        # should include company name, see below
        principals = pd.DataFrame([], columns=['UBINumber', 'BusinessId', 'BusinessName', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName'])

        try:
            search_results = self._get_all_principal_search_results(principal_name)
        except:
            print(f"couldn't get results for {principal_name}")
            return principals
        business_ids = [res['BusinessID'] for res in search_results]
        business_names = [res['BusinessName'] for res in search_results]
        ubi_nums = [res['UBINumber'] for res in search_results]
        
        for id, name in zip(business_ids, business_names):
            business_json = get_business_details(id)
            principals_df = self._extract_principals_business(business_json, id, name)
            
            if len(principals_df[principals_df['PrincipalName'] == principal_name]) > 0:
                principals = pd.concat([self._extract_principals_business(business_json, id, name), principals], ignore_index=True)
            # principals = principals[principals['BusinessId'].isin(all_matches['BusinessId'].values)]
        return principals

    def get_companies_principals(self, business_names_df):
        '''
            Given a list of businesses as a dataframe, return a dataframe with all the businesses and a row for 
            each principal. Therefore if a compnay has multiple principals registered, there will be multiple lines
            for that company in the returned dataframe. 
        '''
        principals = pd.DataFrame([], columns=['BusinessId', 'Agent', 'EntityType', 'PrincipalID', 'PrincipalName'])
        for business in business_names_df['BusinessId']:
            business_res = get_business_details(business)
            principals = pd.concat([self._extract_principals(business_res, business), principals], ignore_index=True)
        
        merged_principals = pd.merge(business_names_df, principals, on='BusinessId', how='left')
        
        return merged_principals

    def group_companies_by_principals(self, principal_match_list: pd.DataFrame):
        """
            Given a list of businesses with one line for each principal registered for that business, returns 
            a dataframe where companies are grouped by whether they share a principal. 
            
            principal_match_list is an output from previous steps, like the dataframe `all_matches_principals.csv`
        """
        print(f"Saving to {self.output_path}{self.output_name}")
        columns=['SearchTerm', 'BusinessName', 'PotentialRelatedCompany', 'UBINumber', 'BusinessId', 'Address', 
                'Status', 'Agent', 'Principals', 'isMatch', 'notes']
        results = pd.DataFrame([], columns)
        for idx, row in principal_match_list.iterrows():
            possible_matching_companies_df = self._get_all_companies_from_principal_dataframe(principal_match_list, row['PrincipalName'])
            grouped = possible_matching_companies_df.groupby("BusinessName")
            for name, group in grouped:
                principals_list = group["PrincipalName"].tolist()
                principals_list.sort()
                poss_company = group.iloc[0]

                # row['BusinessName']: the name we mapped to from SearchTerm
                # poss_company['BusinessName]: PotentialRelatedCompany
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
            if(idx % 25 == 0): 
                print(f"Processing row {idx} of principal_match_list, results is {len(results)}")
                results.to_csv(f"{self.output_path}\{self.output_name}")
                
        results.to_csv(f"{self.output_path}\{self.output_name}")
        return results