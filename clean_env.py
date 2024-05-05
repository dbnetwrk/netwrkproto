# save this script as clean_env.py

def read_packages(file_path):
    with open(file_path, 'r') as file:
        return set(line.split('==')[0] for line in file if '==' in line)

# Read required and installed packages
required_packages = read_packages('requirements.txt')
installed_packages = read_packages('installed.txt')

# Calculate the difference
to_uninstall = installed_packages - required_packages

# Uninstall packages not in requirements.txt
if to_uninstall:
    import os
    command = "pip uninstall -y " + " ".join(to_uninstall)
    os.system(command)
else:
    print("No packages to uninstall.")
