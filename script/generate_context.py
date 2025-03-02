import os
import requests

# open .context from the current directory
# add each line to a buffer in memory

buffer = []
with open('script/context', 'r') as file:
	buffer = file.readlines()

# Add "Automatically generated context follows:" to the buffer

buffer.append("Automatically generated context follows:\n")

# Add "Project Directory Structure:" to the buffer

buffer.append("Project Directory Structure:\n")

# walk the vie directory, excluding the build directory, the .venv one, and all __pycache__ 
# directories and emit the paths, relative to the top level "vie" directory, to stdout
def compute_project_structure(line_buffer, root="."):
	for dirpath, dirnames, filenames in os.walk(root):
		# Exclude build, .venv, and __pycache__ directories
		dirnames[:] = [d for d in dirnames if d not in ["node_modules", ".vscode", ".pytest_cache", 'build', '.venv', '__pycache__', '.git', '.coverage', 'docs', 'logs']]
		for filename in filenames:
			# append the path but add a newline at the end
			line_buffer.append(os.path.relpath(os.path.join(dirpath, filename), root) + '\n')

compute_project_structure(buffer)

# URL of the file to retrieve
url = "https://raw.githubusercontent.com/wiki/edwillis/vie/src/Vie-Detailed-Design.md"

# Retrieve the file contents
response = requests.get(url)
file_contents = response.text

buffer.append("Detailed design document follows:\n")

# Append the contents to the buffer
buffer.append(file_contents)

# Write the updated buffer to the .context file
if response.status_code == 200:
	with open('.cursorrules', 'w') as file1:
		file1.writelines(buffer)

