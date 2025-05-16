from dataclasses import dataclass
from typing import Optional, Any
import sys
import os
import yaml
import logging
logger = logging.getLogger()


@dataclass
class Config:
    """Class to manage main configuration file
    
    Args:
        database: configuration parameters for the database
    
    """
    database: dict[str, Any]

    @classmethod
    def load(cls, configpath: Optional[str] = None) -> dict[str, Any]:
        """Load class from file
        
        Args:
            configpath: absolute path of the configuration file
        
        """
        # read configuration file from the provided path
        if configpath is not None:
            if os.path.exists(configpath):
                with open(configpath, 'r') as fid:
                    config = yaml.full_load(fid)
            else:
                logger.debug(f'Configuration file {configpath} does not exist.')
                config = None
        else:
            config = None

        # retrive configuration path from environment variable if not provided
        if config is None:
            envconfig = os.environ.get('BEERSHOP_CONFIG')
            if envconfig is not None:
                if os.path.exists(envconfig):
                    if not envconfig.endswith('.yaml'):
                        logger.error(f"Wrong configuration file format. Provided '{envconfig.split('.')[-1]}'. Supported: YAML")
                        sys.exit(1)
                    with open(envconfig, 'r') as fid:
                        config = yaml.full_load(fid)
                else:
                    logger.error('Configuration file from os environ not found.')
                    sys.exit(1)
        
        if config is None:
            logger.error('Configuration file not found. Exiting.')
            sys.exit(1)

        # get database config
        databaseconfig = config.get('database')
        if databaseconfig is None:
            logger.error('Database config not found. Exiting.')
            sys.exit(1)

        return cls(databaseconfig)

