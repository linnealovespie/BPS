"""
Utility functions, mainly for preprocessing data.
Used in experiment notebooks. 
"""
import numpy as np
import pandas as pd
import geopandas as gp
from shapely.geometry import Polygon, LineString, Point
import matplotlib.pyplot as plt

# Some points I've already figured out, usually because they're on the water. 
# Might be better to use addresses
known_updates = {
    'WATERWORKS OFFICE & MARINA': 7, 
    'WATERWORKS OFFICES + MARINA': 7, 
    'NAUTICAL LANDING':7,
    'UNION HARBOR CONDOMINIUM':4,
    'THE PIER AT LESCHI':3,
    'PIER AT LESCHI THE':3
}

# Go through all of the building and lookup their (long, lat) to update what district they're in. 
# Outliers are left with a -1 district code and examined manually later. 
def clean_districts(df, df_districts):
    for idx, row in df.iterrows():
        point = row['geometry']
        district = -1 # Flag an unkonwn district
        for gidx, grow in df_districts.iterrows():
            if(grow['geometry'].intersects(point)): 
                district = grow['C_DISTRICT']
        if(district < 0):
            print( f"Building {row.BuildingName} {idx}/ {row.TaxParcelIdentificationNumber} doesn't have a district {row.geometry} ")
            if(row.BuildingName.upper() in known_updates.keys()):
                district = known_updates[row.BuildingName.upper()]
                print(f"\t Found district {district} for {row.BuildingName}")
        df.at[idx, 'CouncilDistrictCode'] = district
    # Drop lines that don't have any lat, long info
    df = df.drop(df[df['geometry'].is_empty==True].index)

# Plot the district boundaries and building (long, lat) points color-coded by the predicted districts. 
# Extra dark points have a district of -1. 
def plot_points(df, df_districts):
    ax = df_districts['geometry'].plot()
    df['geometry'].plot(ax=ax, c=df.CouncilDistrictCode, markersize=10)

