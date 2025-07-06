# -*- coding: utf-8 -*-
"""
Module for integrating predictions from an external AI stock prediction system.

This module executes the external prediction program, retrieves the results,
and integrates them into the trading portfolio analysis.
"""

import os
import sys
import subprocess
import csv
import logging
import json
from typing import List, Dict, Any, Optional

# Logger configuration
logger = logging.getLogger(__name__)

class PredictionIntegration:
    """Class for integrating predictions from an external system."""

    def __init__(self, prediction_path: str = None):
        """Initializes the PredictionIntegration class instance.
        
        Args:
            prediction_path: The path to the external prediction program.
        """
        self.prediction_path = prediction_path or "C:\\Users\\simon\\Desktop\\Programming\\ai-stock-prediction"
        self.main_script = os.path.join(self.prediction_path, "main.py")
        self.download_script = os.path.join(self.prediction_path, "download_dataset.py")
        self.is_available = True
        
        # Check that the paths exist
        if not os.path.exists(self.prediction_path):
            logger.warning(f"The path to the prediction program does not exist: {self.prediction_path}")
            self.is_available = False
            return
            
        if not os.path.exists(self.main_script):
            logger.warning(f"The main prediction script does not exist: {self.main_script}")
            self.is_available = False
            return
            
        if not os.path.exists(self.download_script):
            logger.warning(f"The dataset download script does not exist: {self.download_script}")
            logger.warning("The system will proceed without updating the data")
            
        # Check that the configuration file exists
        config_path = os.path.join(self.prediction_path, "config.json")
        if not os.path.exists(config_path):
            logger.warning(f"The configuration file does not exist: {config_path}")
            self.is_available = False
            return
        
        logger.info(f"Prediction system found and available at: {self.prediction_path}")
    
    def download_dataset(self) -> bool:
        """Runs the dataset download script.
        
        Returns:
            bool: True if execution was successful, False otherwise.
        """
        try:
            if not os.path.exists(self.download_script):
                logger.warning("Download script not available, skipping dataset update")
                return True
                
            logger.info(f"Starting dataset download script: {self.download_script}")
            
            # Run the download command
            result = subprocess.run(
                [sys.executable, self.download_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Dataset download completed successfully")
            logger.debug(f"Download script output: {result.stdout}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while running the download script: {str(e)}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while running the download script: {str(e)}")
            return False

    def run_prediction(self, symbol: str) -> bool:
        """Runs the external prediction program.
        
        Returns:
            bool: True if execution was successful, False otherwise.
        """
        try:
            logger.info(f"Starting prediction program: {self.main_script} --mode predict --symbol {symbol}")
            
            # Run the command
            result = subprocess.run(
                [sys.executable, self.main_script, "--mode", "predict", "--symbol", symbol],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Prediction program completed successfully")
            logger.debug(f"Program output: {result.stdout}")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while running the prediction program: {str(e)}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while running the prediction program: {str(e)}")
            return False
    
    def get_prediction_file_from_config(self) -> Optional[str]:
        """Reads the prediction file path from the configuration file.
        
        Returns:
            Optional[str]: The path to the prediction CSV file, or None if not found.
        """
        try:
            config_path = os.path.join(self.prediction_path, "config.json")
            
            if not os.path.exists(config_path):
                logger.error(f"Configuration file not found: {config_path}")
                return None
                
            logger.info(f"Reading configuration file: {config_path}")
            
            with open(config_path, 'r') as config_file:
                config_data = json.load(config_file)
            
            # Extract the CSV file path from the settings
            if 'prediction' in config_data and 'last_csv' in config_data['prediction']:
                csv_path = config_data['prediction']['last_csv']
                
                # Check that the file exists
                if os.path.exists(csv_path):
                    logger.info(f"Prediction file found in config: {csv_path}")
                    return csv_path
                else:
                    logger.error(f"The prediction file specified in the config does not exist: {csv_path}")
                    return None
            else:
                logger.error("Configuration 'prediction.last_csv' not found in config.json")
                return None
                
        except Exception as e:
            logger.error(f"Error while reading the configuration file: {str(e)}")
            return None
    
    def read_prediction_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads prediction data from the CSV file.
        
        Args:
            file_path: The path to the prediction CSV file.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing the prediction data.
        """
        try:
            prediction_data = []
            
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                # Skip the header
                header = next(reader, None)
                
                # Check if the file has a single 'predicted' column
                if header and len(header) == 1 and header[0].strip().lower() == 'predicted':
                    logger.info("Detected CSV format with single 'predicted' column")
                    # Read numeric values from the 'predicted' column
                    for i, row in enumerate(reader):
                        if row and len(row) > 0 and row[0].strip():
                            try:
                                value = float(row[0].strip())
                                # Use an index as a temporary date
                                prediction_data.append({
                                    "date": f"Day {i+1}",
                                    "prediction": value
                                })
                            except ValueError:
                                logger.warning(f"Unable to convert value '{row[0]}' to float")
                else:
                    # Traditional format with date and prediction
                    logger.info("Detected traditional CSV format with date and prediction")
                    # Rewind the file and skip the header again
                    csvfile.seek(0)
                    next(reader, None)
                    
                    for row in reader:
                        if len(row) >= 2:  # Ensure there are at least two columns
                            prediction_data.append({
                                "date": row[0] if len(row) > 0 else "",
                                "prediction": float(row[1]) if len(row) > 1 and row[1] else 0.0,
                            })
            
            logger.info(f"Read {len(prediction_data)} prediction records from file {file_path}")
            return prediction_data
        except Exception as e:
            logger.error(f"Error while reading the prediction file {file_path}: {str(e)}")
            return []
    
    def format_prediction_for_prompt(self, prediction_data: List[Dict[str, Any]]) -> str:
        """Formats prediction data for the Together AI prompt.
        
        Args:
            prediction_data: List of dictionaries containing the prediction data.
            
        Returns:
            str: Formatted text for the prompt.
        """
        if not prediction_data:
            return "No prediction data available."
        
        formatted_text = "FUTURE PREDICTIONS:\n"
        
        for item in prediction_data:
            date = item.get("date", "")
            prediction = item.get("prediction", 0.0)
            formatted_text += f"- {date}: ${prediction:.2f}\n"
        
        return formatted_text
    
    def get_predictions(self, symbol) -> Optional[str]:
        """Executes the entire process of obtaining predictions.
        
        Returns:
            Optional[str]: Formatted text with predictions, or None in case of error.
        """
        # Check if the prediction system is available
        if not self.is_available:
            logger.warning("Prediction system not available, analysis will proceed without predictions")
            return None
            
        try:
            # First download the updated dataset
            logger.info("Starting download of updated dataset")
            if not self.download_dataset():
                logger.warning("Unable to download updated dataset, proceeding with existing data")
            
            # Run the prediction program
            if not self.run_prediction(symbol):
                logger.error("Unable to run the prediction program")
                return None
            
            # Get the prediction file path from config.json
            prediction_file = self.get_prediction_file_from_config()
            if not prediction_file:
                logger.error("Unable to find the prediction file in config.json")
                return None
            
            # Read the prediction data
            prediction_data = self.read_prediction_data(prediction_file)
            if not prediction_data:
                logger.error("No prediction data read from file")
                return None
            
            # Format the data for the prompt
            formatted_predictions = self.format_prediction_for_prompt(prediction_data)
            
            logger.info("Predictions obtained and formatted successfully")
            return formatted_predictions
        
        except Exception as e:
            logger.error(f"Error while obtaining predictions: {str(e)}")
            return None