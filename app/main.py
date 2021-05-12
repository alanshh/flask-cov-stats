import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import pathlib
import json
import os
import glob
from flask_frozen import Freezer
from flask import Flask, render_template, request, url_for



def plotData(statType, countyfile, start=None, end=None):
    """
    Plots reported or cumulative Covid-19 cases on respectively a bar or line chart
    and returns it as json dictionary and altair chart class. With time range functionality. 

    Args:
        statType(str): specifies type of statistic. Decides whether to create 'cumulative' or 'reported' type of chart
        countyfile(str): name of csv file to read data from. By default, file with all county data is used
        start(str): optional: the start date of the chart timeline. By default the start of csv file. Format: DD.MM.YYYY
        end(str): optional: the end date of the chart timeline. By default the end of csv file. Format: DD.MM.YYYY
        
        example: plotData("reported", "agder.csv", start='23.05.2020', end='30.10.2020')
    Returns:
        jsonDict(dict): plot json structure
        chart(altair.Chart): the generated chart in altair chart class structure

    """
    #get directory 
    currentDir = pathlib.Path(__file__).parent.absolute()
    countyDir = str(currentDir)+"/covcounties/"
    os.chdir(countyDir)
    statTypeDict = {"reported": "Nye tilfeller", "cumulative": "Kumulativt antall"}
    if statType not in statTypeDict:
        raise ValueError("Specify a statistic type of reported or cumulative case")
    #create dataframe from given csv file (standard is alle_fylker.csv)
    data = pd.read_csv(countyDir+countyfile, usecols=['Dato', statTypeDict[statType]], dayfirst=True, infer_datetime_format=True, parse_dates=['Dato'])
    #if date ranges are not set
    if start is None:
        start = data['Dato'].iloc[0]
    if end is None:
        end = data['Dato'].iloc[-1]
    #convert given dates into datetime objects
    start = pd.to_datetime(start, format='%d.%m.%Y')
    end = pd.to_datetime(end, format='%d.%m.%Y')
    #ensure dates in dataframe are correct dtype
    data['Dato'] = pd.to_datetime(data['Dato']) 
    #find range and alter dataframe accordingly
    mask = (data['Dato'] > start) & (data['Dato'] <= end)
    data = data.loc[mask]
    #Create base chart
    chart = alt.Chart(data).encode(
        x='Dato',
        y=statTypeDict[statType],
        tooltip=['Dato', statTypeDict[statType]] 
    ).properties(
        title=statTypeDict[statType]+" i "+countyfile.capitalize().replace('_',' ')[:-4]
    ).interactive()

     #Generate appropriate type of chart
    if(statType == "reported"):
        chart = chart.mark_bar().encode(color=statTypeDict[statType])
    else:
        chart = chart.mark_area()

    #Save to file and return json string
    json = chart.to_json()
    return json, chart

    
def plot_reported_cases(countyfile="alle_fylker.csv", start=None, end=None):
    """
    Plots all reported cases from given covid-19 data csv file to a bar chart
    and returns it as json dictionary and altair chart clas.
    
    Args:
        countyfile(str): name of csv file
        start(str): optional: the start date of the bar chart timeline. By default the start of csv file. Format: DD.MM.YYYY
        end(str): optional: the end date of the bar chart timeline.By default the end of csv file. Format: DD.MM.YYYY

    Returns:
        jsonDict(dict): plot json structure
        chart(altair.Chart): the generated chart in altair chart class structure
    """
    return plotData("reported", countyfile, start, end)

def plot_cumulative_cases(countyfile="alle_fylker.csv", start=None, end=None):
    """
    Plots all cumulative cases from given covid-19 data csv file to a line chart
    and returns it as json dictionary and altair chart clas.
    
    Args:
        countyfile(str): name of csv file
        start(str): optional: the start date of the bar chart timeline. By default the start of csv file. Format: DD.MM.YYYY
        end(str): optional: the end date of the bar chart timeline. By default the end of csv file. Format: DD.MM.YYYY
    Returns:
        jsonDict(dict): plot json structure
        chart(altair.Chart): the generated chart in altair chart class structure
    """
    return plotData("cumulative", countyfile, start, end)


def plot_both(countyfile="alle_fylker.csv", start=None, end=None):
    """
    Plots both cumulative and reported cases from given covid-19 data csv file
    to one illustration using, respectively, a line chart and bar chart
    and returns as json dictionary.
     
    Args:
        countyfile(str): name of csv file
        start(str): optional: the start date of the bar chart timeline. By default the start of csv file. Format: DD.MM.YYYY
        end(str): optional: the end date of the bar chart timeline. By default the end of csv file. Format: DD.MM.YYYY
    Returns:
        jsonDict(str): plot json structure in dictionary
    """

    #get both plots
    reported = plot_reported_cases(countyfile, start, end)[1]
    cumulative = plot_cumulative_cases(countyfile, start, end)[1].mark_line()


    reported = reported.encode(
        alt.Y('Nye tilfeller',
        axis=alt.Axis(title='Nye tilfeller', titleColor='blue'))
    )
    cumulative = cumulative.encode(
        alt.Y('Kumulativt antall',axis=alt.Axis(title='Kumulativt antall', titleColor='red')),
        color=alt.value('red')
    )
    combo = alt.layer(reported, cumulative).resolve_scale(y = 'independent').properties(
         title="Kumulativt antall og nye tilfeller av smittede"
    )
    

    #Save to file and return json string
    json = combo.to_json()
    return json 

def plot_norway():
    """
    Plots number of cases per 100k on each county on a chart depicting Norway.

    Returns:
        jsonDict(dict): plot json structure in dictionary

    """
    #get directory 
    currentDir = pathlib.Path(__file__).parent.absolute()
    countyDir = str(currentDir)+"/covcounties/"
    os.chdir(countyDir)
    #create dataframe from county csv file
    data = pd.read_csv(countyDir+"reported-county.csv")
    #extract counties from json file
    counties = alt.topo_feature("https://raw.githubusercontent.com/deldersveld/topojson/master/countries/norway/norway-new-counties.json", "Fylker")
    #nearest selection of county 
    nearest = alt.selection(type="single", on="mouseover", fields=["properties.navn"], empty="none")
    #plot country chart
    country_chart = alt.Chart(counties).mark_geoshape().encode(
        #hover effect
        tooltip=[
            alt.Tooltip("properties.navn:N", title="Fylke"),
            alt.Tooltip("Insidens:Q", title="Antall meldte tilfeller per 100k")
        ],
        color=alt.Color("Insidens:Q", scale=alt.Scale(scheme="reds"),
            legend=alt.Legend(title="Antall meldte tilfeller per 100k")),
            stroke=alt.condition(nearest, alt.value("gray"), alt.value(None)),
            opacity=alt.condition(nearest, alt.value(1), alt.value(0.8)),
    #lookup number of cases from dataframe and map it to counties
    ).transform_lookup(
        lookup="properties.navn",
        from_=alt.LookupData(data, "Category", ["Insidens"])
    ).properties(
        width=500,
        height=600,
        title="Antall meldte tilfeller per 100k i hvert fylke"
    ).add_selection(nearest)

    #Save to file and return json string   
    json = country_chart.to_json()

    #Fix json translation of null to None
    #jsonDict['encoding']['stroke']['value'] = "null"
    
    return json
    

app = Flask(__name__, template_folder='templates', static_url_path='/static/')
@app.route("/", methods=['GET', 'PUT', 'POST'])
def display_covid_county_data():
    """
    Gets all types of plots and renders them on a html template.

    Returns:
        *html(str)*: returns the rendered html in string
    """

    county = request.args.get('counties')
    #initialize plots to show data for all counties
    if county is None:
        county = "alle_fylker.csv"

    reported_json = plot_reported_cases(county)[0]
    cumulative_json = plot_cumulative_cases(county)[0]
    combo_json = plot_both(county)
    norway_json = plot_norway()
    #Get all county data filenames
    county_names=[]
    for county_csv in glob.glob("*.csv"):
        if(county_csv != "reported-county.csv"):
            county_names.append(county_csv)

    return render_template('image.html', json=cumulative_json, json2=reported_json, json3=combo_json, json4=norway_json, counties=county_names)


#Help page urls
@app.route("/help", methods=['GET'])
def help_page(path="/help/index.html"):
    return render_template(path)

@app.route("/help/genindex.html", methods=['GET'])
def c_page(path="/help/genindex.html"):
    return render_template(path)

@app.route("/help/py-modindex.html", methods=['GET'])
def com_page(path="/help/py-modindex.html"):
    return render_template(path)




if __name__ == "__main__":
    app.run()