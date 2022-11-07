# -*- coding: utf-8 -*-
"""Access_Earth_Engine_Data.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1M6-4vQk-9zJS2DBTZ3DLUWdRQ0h4YHV0
"""

#!pip install earthengine-api
# !pip install geopandas
# !pip install geemap

try:
  import ee
  #ee.Authenticate()
  ee.Initialize()
except:
  import ee
  ee.Authenticate()
  ee.Initialize()

import geopandas as gpd
import geemap
import os
import glob
import pandas as pd

def get_monthly_df(**configs):
    configs = configs
    data = configs["data"]
    band_name = configs['band_name']
    start_date = configs['start_date']
    aoi_shp = configs['aoi_shp']
    scale = configs['scale']

    data_collection = data.select(band_name)
    aoi = geemap.shp_to_ee(aoi_shp)
    def stat(n):
       date = ee.Date(start_date).advance(n,'month')
       month = date.get("month")
       year = date.get("year")
       date_dic = ee.Dictionary({'Date':date.format('yyyy-MM')})
       monthly_pollutant = (data_collection.filter(ee.Filter.calendarRange(year, year, 'year'))
            .filter(ee.Filter.calendarRange(month, month, 'month')).filterBounds(aoi).median()
            .reduceRegion(
                reducer = ee.Reducer.minMax().combine(ee.Reducer.mean(), '', True),
                geometry = aoi,
                scale = scale))
       return date_dic.combine(monthly_pollutant)
    mean_midmax = ee.List.sequence(0, 11*1).map(stat)
    dataframe = pd.DataFrame(mean_midmax.getInfo())
    return dataframe


def format_df(dataframe_formatted):
  col_name = dataframe_formatted.columns
  columns = [col_name[0]]
  for i in range(1,len(col_name)):
    new_col = col_name[i].split("_")[0] + "_" + col_name[i].split("_")[-1] + "_(mol/m^2)"
    columns.append(new_col)
  dataframe_formatted.columns = columns
  return dataframe_formatted



def get_daily_avg(collection,aoi,band_name,start_date,end_date,col_name):
  def daily_mean(img):
    daily_avg = img.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=1113.2).get('NO2_column_number_density')
    return img.set('date', img.date().format('YYYY-MM-dd')).set('mean',daily_avg)
  dataset = collection.select(band_name).filterDate(start_date, end_date).filterBounds(aoi)
  daily_avg_img = dataset.map(daily_mean)
  daily_avg_list = daily_avg_img.reduceColumns(ee.Reducer.toList(2), ['date','mean']).values()
  df = pd.DataFrame(daily_avg_list.getInfo()[0], columns=['Date','mean'])

  def format(df):
    final_df = df.groupby(pd.PeriodIndex(df['Date'], freq="d"))[df.columns].mean().reset_index()
    final_df = final_df.set_index('Date').sort_index()
    final_df = final_df.reindex(pd.period_range(start_date,end_date,freq='d').tolist()).reset_index()
    final_df = final_df.rename(columns = {'mean':col_name})
    final_df["Date"] = pd.to_datetime(final_df["Date"].astype(str))
    return final_df
  return format(df)
  
  
  
  
 def download_img(dataset,band_name,start_date,end_date,aoi):
  img = dataset.select(band_name).filterDate(start_date,end_date).filterBounds(aoi).mean()
  img = img.clip(aoi)
  task = ee.batch.Export.image.toDrive(image=img,
                                     description= band_name + "_" + str(start_date) + "_" + str(end_date),
                                     scale=1113.2,
                                     region=aoi,
                                     folder = 'BSA',
                                     crs='EPSG:4326',
                                     fileFormat='GeoTIFF',
                                     maxPixels = 1e13)
  task.start()
  print(task.status(), end = '\n')
  return task