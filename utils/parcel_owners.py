import pandas as pd
from bs4 import BeautifulSoup
import requests
import re
import json

class ParcelLookupHelper:
    def __init__(self, output_path: str):
        self.output_path = output_path # Absolute path to where files will be saved
        self.parcel_base_url = 'https://blue.kingcounty.com/Assessor/eRealProperty/Detail.aspx?ParcelNbr='
    
    def _get_parcel_df(self):
        return pd.DataFrame([], columns=['TaxParcelIdentificationNumber', 'Owner'])
    
    def _write_parcel_owner_csv(self, parcel_df, file_name):
        print(f'Writing parcel owners to CSV: {self.output_path}/{file_name}.csv')
        parcel_df.to_csv(f'{self.output_path}/{file_name}.csv')
                     
    def _write_unit_details_to_json(self, unit_details, file_name):
        print(f'Writing unit details to JSON: {self.output_path}/{file_name}.csv')
        with open(f'{self.output_path}/{file_name}_unit_details.csv', 'w') as fp:
            json.dump(unit_details, fp)
        
    def _get_tax_id_str(self, tax_parcel_id_number: int):
        """
        For a given tax ID number, `tax_parcel_id_number`, 
        reformat the tax ID as it will be used in the property detail page URL.
        """
        id_len = len(str(tax_parcel_id_number))
        prefix = "0"*(10 - id_len)
        return prefix + str(tax_parcel_id_number)
                     
    def _make_parcel_soup(self, tax_parcel_id_number: int):
        """
        Fetch the HTML of a Property Detail page for a given tax ID number, `tax_parcel_id_number`.
        Returns a BeautifulSoup object 
        """
        url = self.parcel_base_url + self._get_tax_id_str(tax_parcel_id_number)
        r = requests.get(url)
        html_soup = BeautifulSoup(r.text, 'html.parser')
        data_not_found = html_soup.find('span', text='No data found.')
        if data_not_found:
            return None
        return html_soup
    
    def _get_owner_name_from_soup(self, soup: object):
        """
        Extract the owner name from a given BeautifulSoup object, `soup`, of a Property Detail page.
        """
        title = soup.find('th', text = re.compile('SALES HISTORY'))
        if not title:
            return 'NOT_FOUND'
        parent = title.parent
        next_tr = title and parent.find_next('tr')
        table = next_tr and next_tr.table
        return table and table.find_all('td')[5].text
    
    def _get_num_units_and_types_from_soup(self, soup: object):
        """
        Given a BeautifulSoup object, `soup`, of a Property Detail page, extract:
            - the number of units in the building
            - the unit types
            - the sq ft of each unit type
            - number of bed/bath rooms in each unit type
        """
        title = soup.find('span', text = 'Unit Breakdown')
        if not title:
            return { 'numUnits': 'NOT_FOUND', 'unitDetails': 'NOT_FOUND' }
                     
        table = title and title.find_next('div').table
        table_rows = table and table.find_all('tr')[1:]
        cells = table_rows and [row.find_all('td') for row in table_rows]
        table_data = []
        
        for c in cells:
            table_data.append([span.text for span in c])
            total_units = sum([int(row[1]) for row in table_data])
            dict_keys = ['type', 'number', 'sqft', 'bed', 'bath']
            units = [dict(zip(dict_keys, row)) for row in table_data]
        return { 'numUnits': total_units, 'unitDetails': units }
    
    def _scrape_parcel_owners(self, tax_parcel_id_numbers: list, file_name: str):
        """
        Given a list of `tax_parcel_id_numbers`, look up the owners and save the results to a CSV, `file_name`.
        """
        parcel_df = self._get_parcel_df()
        idx = 0
        for id in tax_parcel_id_numbers:
            parcel_soup = self._make_parcel_soup(id)
            if not parcel_soup:
                parcel_df.loc[len(parcel_df.index)] = [id, 'NOT FOUND']
            else:
                owner_name = self._get_owner_name_from_soup(parcel_soup)
                parcel_df.loc[len(parcel_df.index)] = [id, owner_name]
            if(idx % 25 == 0): 
                print(f"Processing row {idx} of {len(tax_parcel_id_numbers)} parcel owners")
                self._write_parcel_owner_csv(parcel_df, file_name)
            idx += 1

        self._write_parcel_owner_csv(parcel_df, file_name)
                     
    def _scrape_parcel_owners_and_unit_details(self, tax_parcel_id_numbers: list, file_name: str):
        """
        Given a list of `tax_parcel_id_numbers`, looks up:
            - the building owners, saved to a CSV, `file_name`
            - the unit details for each building, saved to a JSON, `file_name`_unit_details
        """
        parcel_df = self._get_parcel_df()
        unit_details_json = {}

        for id in tax_parcel_id_numbers:
            parcel_soup = self._make_parcel_soup(id)
            if not parcel_soup:
                parcel_df.loc[len(parcel_df.index)] = [id, 'NOT FOUND']
                unit_details_json[id] = {}
            else:
                owner_name = self._get_owner_name_from_soup(parcel_soup)
                parcel_df.loc[len(parcel_df.index)] = [id, owner_name]
                unit_details = self._get_num_units_and_types_from_soup(parcel_soup)
                unit_details['Owner'] = owner_name
                unit_details_json[id] = unit_details
        
        self._write_parcel_owner_csv(parcel_df, file_name)
        self._write_unit_details_to_json(unit_details_json, file_name)
    
    def scrape_parcel_owners(self, tax_parcel_id_numbers: list, file_name: str, get_unit_details: bool = False):
        """
        Given a list of `tax_parcel_id_numbers`, looks up:
            - the building owners and save to a CSV, `file_name`
            - if `get_unit_details` is set to `True`, look the unit details for each building and save to a JSON, `file_name`_unit_details
        """
        if get_unit_details:
            self._scrape_parcel_owners_and_unit_details(tax_parcel_id_numbers, file_name)
        else:
            self._scrape_parcel_owners(tax_parcel_id_numbers, file_name)
