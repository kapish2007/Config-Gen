import os
import json
import time
from datetime import date, datetime
from csv import DictReader
from jinja2 import Environment, FileSystemLoader
from termcolor import cprint

def build_template(
    template_file: str = "switch.j2",
    parameters_file: str = "01_parameters.csv",
    vlans_file: str = "02_vlans.csv",
    etherchannels_file: str = "03_etherchannels.csv",
    port_mapping: str = "04_port-mapping.csv"
):
    """Generates Cisco configuration templates for each hostname in CSVs"""

    def raise_helper(msg: str):
        raise SystemExit(cprint(msg, "red"))

    env = Environment(
        loader=FileSystemLoader("./"), trim_blocks=True, lstrip_blocks=True
    )
    env.globals["raise"] = raise_helper
    template = env.get_template(name=template_file)
    template.globals["now"] = datetime.now().replace(microsecond=0)

    if not os.path.exists("configs"):
        os.mkdir("configs")

    # Read CSVs and group data by hostname
    hostname_data = {}

    # Helper function to load CSV data into hostname_data dictionary
    def load_csv_to_hostname_data(file_path, key):
        with open(file=file_path, mode="rt", encoding="utf-8") as f:
            for row in DictReader(f):
                hostname = row["hostname"]
                if hostname not in hostname_data:
                    hostname_data[hostname] = {"hostname": hostname, "vlans": [], "etherchannels": [], "interfaces": []}
                hostname_data[hostname][key].append(row)

    # Load each CSV based on its type
    load_csv_to_hostname_data(parameters_file, "parameters")
    load_csv_to_hostname_data(vlans_file, "vlans")
    load_csv_to_hostname_data(etherchannels_file, "etherchannels")
    load_csv_to_hostname_data(port_mapping, "interfaces")

    # Process each hostname's data
    for hostname, data in hostname_data.items():
        # Generate JSON structure for the hostname
        json_data = {
            "hostname": hostname,
            "parameters": data.get("parameters", [{}])[0],  # Assuming single set of parameters per hostname
            "vlans": data["vlans"],
            "etherchannels": data["etherchannels"],
            "interfaces": data["interfaces"]
        }

        # Write the JSON file for the hostname
        json_filename = f"{hostname}_config.json"
        json_path = os.path.join("configs", json_filename)
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=4)

        # Validate configuration
        validation = validate_config(schema=json_path)
        if validation.get("is_validated"):
            # Render the configuration template for the hostname
            config = template.render(json_data)
            config_filename = f"{hostname}_{date.today()}.txt"
            config_path = os.path.join("configs", config_filename)
            with open(config_path, "w", encoding="utf-8") as cfg_file:
                cfg_file.write(config)

            # Display success message
            cprint(f"Configuration file '{config_filename}' created!", "green")

            # Prompt to open the config file
            decision = input(f"Do you want to open {config_filename} now? [y/N]: ").lower() or "n"
            if decision == "y":
                cprint(f"Opening '{config_filename}', please wait...", "cyan")
                time.sleep(1)
                TextEditor.open(config_path, new=0)
            else:
                cprint(f"INFO: '{config_filename}' created in configs directory.", "blue")
        else:
            # Handle validation errors
            cprint(f"Validation failed for {hostname}. Check errors below:", "red")
            for k, val in validation.get("errors", {}).items():
                cprint(f"Errors: {k}: {val}", "red")
