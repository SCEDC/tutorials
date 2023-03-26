# Tutorials

## SCEDC Web Services

*  [Retrieve event, station and waveform data for the 2019 Ridgecrest 7.1](../main/jupyter-notebooks/Ridgecrest7_1_SCEDC_web_services.ipynb)

## SCEDC PySTP

* [Retrieve and plot event triggered data and phase picks using PySTP](../main/jupyter-notebooks/PySTP_Tutorial.ipynb)

## SCEDC Public Data Set (PDS)  
  
*  [Retrieve continuous waveform data from SCEDC PDS](../main/jupyter-notebooks/PDS_fetch_continuous_data/PDS_fetch_continuous_data.ipynb) 
  
    This tutorial uses the *Clickable Station Map* to query and retrieve a list of stations. It then, leverages the SCEDC FDSN availability web service to get time spans for waveform data for these stations. Finally, it retrieves data from PDS for a time span.

## SCEDC AWS Ridgecrest DAS  

*  [Retrieve DAS waveform data from AWS and basic processing](../main/jupyter-notebooks/DAS_aws_Ridgecrest/access_aws_data.ipynb) 
  
    This tutorial shows how to download distributed acoustic sensing (DAS) data from the Ridgecrest array and how to perform simple processing operations on the data (e.g., plotting earthquake strain, computing cross-correlations).
    
## Sample AWS Boto3 script

*  [Sample boto3 script to access SCEDC PDS](../main/jupyter-notebooks/boto3_demo.ipynb)

   This script uses boto3 to retrieve a waveform file from the SCEDC PDS and print waveform information using Obspy functions.

## Accessing SCEDC/SCSN data via MATLAB 

*  Retrieve event, station, and waveform data from SCEDC using MATLAB: [Regular .m Script](../main/scedc_access_tutorial.m) or [Live Script](../main/scedc_access_tutorial.mlx)
*  Note that both versions contain the same information and code.
  
    This tutorial demonstrates how to retrieve event, station, and waveform data using irisFetch in MATLAB and make basic plots with the data. The tutorial also briefly covers waveform access and plotting with the GISMO toolbox.
