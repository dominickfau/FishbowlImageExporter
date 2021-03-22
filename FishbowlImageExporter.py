import mysql.connector
from tkinter import *
import tkinter.messagebox as messagebox
from tkinter.ttk import Progressbar
import tkinter.ttk as ttk
from tkinter import filedialog
import base64
import os.path
import shutil
import time
import threading


root = Tk()

#TODO: Change root window title.
root.title("Read Images")

width = 600
height = 200
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width/2) - (width/2)
y = (screen_height/2) - (height/2)
root.geometry("%dx%d+%d+%d" % (width, height, x, y))
root.resizable(0, 0)

#========================================VARIABLES========================================
CHARS_NOT_ALLOWED = ['\\', '/', '*', '?', ':', '<', '>', '|']
REPLACE_WITH = '_'

imageSaveFolder = ""
authSet = False

auth = {"host": "127.0.0.1",
        "port": "3306",
        "user": "gone",
        "password": "fishing",
        "database": "qes"
        }
        
#========================================METHODS==========================================
def Database():
    try:
        connectionParms = auth
        db = mysql.connector.connect(**connectionParms)
    except mysql.connector.Error as err:
        info = str("Something went wrong in Database: {}".format(err))
        if err.errno == 2003:
            info = "Could not connect to the database. Please double check MySQL connection settings. If this error persists make sure the database server is running and excepting connections."
            messagebox.showerror("MySQL", info)
            AskForMySQLLogin()
            return
        messagebox.showerror("MySQL", info)
        return
    return db


def get_cursor():
    global conn
    try:
        conn.ping(reconnect=True, attempts=5, delay=3)
    except mysql.connector.Error as err:
        conn = Database()
    except NameError:
        conn = Database()
    if not conn:
        return None
    return conn.cursor()
    

def EncodedImage(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')


def WriteImage(saveToFolder, FileName, FileExtention, b64ImageData):
    # Replace invalid filename chars.
    for item in CHARS_NOT_ALLOWED:
        FileName = FileName.replace(item, REPLACE_WITH)

    SaveFilePathName = saveToFolder + "/" + FileName + "." + FileExtention
    imgdata = base64.b64decode(b64ImageData)
    with open(SaveFilePathName, 'wb') as f:
        f.write(imgdata)

def SaveImages():
    global imageSaveFolder
    itemsToDelete = os.listdir(imageSaveFolder)
    totalItems = len(itemsToDelete)
    for x, filename in enumerate(itemsToDelete):
        file_path = os.path.join(imageSaveFolder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            messagebox.showerror("File Delete","Failed to delete file from selected folder: %s. Reason: %s" % (filename, e))
            return
        label_count.config(text=f"Removing files... {str(x + 1)} of {str(totalItems)} Removed.")
        progress['value'] = ((x + 1) / totalItems) * 100

    cursor = get_cursor()
    label_count.config(text="Saving Part Images... 0 of 0 Saved.")
    progress['value'] = 0
    if not cursor:
        return
    partPhotoCountQuery = """SELECT COUNT(*) FROM image WHERE image.tableName = 'part'"""
    partPhotoDataQuery = """SELECT part.num, image.imageFull, SUBSTRING_INDEX(image.type,'/',-1)
                    FROM image
                    JOIN part ON image.recordId = part.id
                    WHERE image.tableName = "part"
                    LIMIT %s, 1"""

    productPhotoCountQuery = """SELECT COUNT(*) FROM image WHERE image.tableName = 'product'"""
    productPhotoDataQuery = """SELECT product.num, image.imageFull, SUBSTRING_INDEX(image.type,'/',-1)
                    FROM image
                    JOIN product ON image.recordId = product.id
                    WHERE image.tableName = "product"
                    LIMIT %s, 1"""

    # Save Part Images
    try:
        cursor.execute(partPhotoCountQuery,)
        totalPhotos = int(cursor.fetchall()[0][0])
        label_count.config(text=f"Saving Part Images... 0 of {str(totalPhotos)} Saved.") 
    except mysql.connector.Error as e:
        print(e)

    for x in range(totalPhotos):
        try:
            cursor.execute(partPhotoDataQuery, (x,))
            photoData = cursor.fetchall()
        except mysql.connector.Error as e:
            print(e)
        WriteImage(imageSaveFolder, "Part " + photoData[0][0], photoData[0][2], photoData[0][1])
        label_count.config(text=f"Saving Part Images... {str(x + 1)} of {str(totalPhotos)} Saved.")
        progress['value'] = ((x + 1) / totalPhotos) * 100
    
    # Save Product Images
    label_count.config(text="Saving Product Images... 0 of 0 Saved.")
    progress['value'] = 0
    try:
        cursor.execute(productPhotoCountQuery,)
        totalPhotos = int(cursor.fetchall()[0][0])
        label_count.config(text=f"Saving Product Images... 0 of {str(totalPhotos)} Saved.") 
    except mysql.connector.Error as e:
        print(e)

    for x in range(totalPhotos):
        try:
            cursor.execute(productPhotoDataQuery, (x,))
            photoData = cursor.fetchall()
        except mysql.connector.Error as e:
            print(e)
        WriteImage(imageSaveFolder, "Product " + photoData[0][0], photoData[0][2], photoData[0][1])
        label_count.config(text=f"Saving Product Images... {str(x + 1)} of {str(totalPhotos)} Saved.")
        progress['value'] = ((x + 1) / totalPhotos) * 100

    cursor.close()
    conn.close()
    showOutputFolder = messagebox.askyesno("MySQL", "All images have been saved. Would you like to open the output folder?")

    if showOutputFolder:
        os.startfile(imageSaveFolder)
    label_count.config(text="0 of 0 Saved.")
    progress['value'] = 0


def OnMySqlSubmitClick():
    global auth
    global authSet
    ipAddress = ipAddressEntry.get()
    portNumber = portNumberEntry.get()
    databaseName = databaseNameEntry.get()
    username = userNameEntry.get()
    password = passwordEntry.get()
    
    if len(ipAddress) == 0:
        messagebox.showerror("Fishbowl Database Login", "Server ID Address can not be blank.", parent=mysql_creds)
        return
    if len(portNumber) == 0:
        messagebox.showerror("Fishbowl Database Login", "Server Port Number can not be blank.", parent=mysql_creds)
        return
    if len(databaseName) == 0:
        messagebox.showerror("Fishbowl Database Login", "Database Name can not be blank.", parent=mysql_creds)
        return
    if len(username) == 0:
        messagebox.showerror("Fishbowl Database Login", "Username can not be blank.", parent=mysql_creds)
        return
    if len(password) == 0:
        messagebox.showerror("Fishbowl Database Login", "Password can not be blank.", parent=mysql_creds)
        return
        
    auth["host"] = ipAddress
    auth["port"] = portNumber
    auth["database"] = databaseName
    auth["user"] = username
    auth["password"] = password
    root.focus()
    mysql_creds.destroy()
    authSet = True

def mysqlCredsExit():
    mysql_creds.destroy()
    root.focus_force()

def AskForMySQLLogin():
    global auth
    global mysql_creds
    mysql_creds = Toplevel(root)
    mysql_creds.title("Fishbowl Database Info")
    mysql_creds.wm_attributes("-topmost", 1)
    mysql_creds.protocol("WM_DELETE_WINDOW", mysqlCredsExit)

    width = 300
    height = 200
    screen_width = mysql_creds.winfo_screenwidth()
    screen_height = mysql_creds.winfo_screenheight()
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    mysql_creds.geometry("%dx%d+%d+%d" % (width, height, x, y))

    ipAddressLabel = Label(mysql_creds, text="Server IP:")
    ipAddressLabel.grid(row=0, column=0, sticky="E")
    global ipAddressEntry
    ipAddressEntry = Entry(mysql_creds, width=30)
    ipAddressEntry.grid(row=0, column=1, padx=3, pady=3)
    ipAddressEntry.delete(0, "end")
    ipAddressEntry.insert(0, auth["host"])
    
    portNumberLabel = Label(mysql_creds, text="Server Port:")
    portNumberLabel.grid(row=1, column=0, sticky="E")
    global portNumberEntry
    portNumberEntry = Entry(mysql_creds, width=30)
    portNumberEntry.grid(row=1, column=1, padx=3, pady=3)
    portNumberEntry.delete(0, "end")
    portNumberEntry.insert(0, auth["port"])
    
    databaseNameLabel = Label(mysql_creds, text="Database Name:")
    databaseNameLabel.grid(row=2, column=0, sticky="E")
    global databaseNameEntry
    databaseNameEntry = Entry(mysql_creds, width=30)
    databaseNameEntry.grid(row=2, column=1, padx=3, pady=3)
    databaseNameEntry.delete(0, "end")
    databaseNameEntry.insert(0, auth["database"])

    userNameLabel = Label(mysql_creds, text="Username:")
    userNameLabel.grid(row=3, column=0, sticky="E")
    global userNameEntry
    userNameEntry = Entry(mysql_creds, width=30)
    userNameEntry.grid(row=3, column=1, padx=3, pady=3)
    userNameEntry.delete(0, "end")
    userNameEntry.insert(0, auth["user"])

    passwordLabel = Label(mysql_creds, text="Password:")
    passwordLabel.grid(row=4, column=0, sticky="E")
    global passwordEntry
    passwordEntry = Entry(mysql_creds, width=30, show="*")
    passwordEntry.grid(row=4, column=1, padx=3, pady=3)
    passwordEntry.delete(0, "end")
    passwordEntry.insert(0, auth["password"])
    
    submitButton = Button(mysql_creds, text="Apply Settings", command=OnMySqlSubmitClick)
    submitButton.grid(row=10, column=0, columnspan=3, padx=3, pady=3)
    mysql_creds.focus()
    databaseNameEntry.focus()

def ReadAll():
    global imageSaveFolder
    global authSet
    if not authSet:
        messagebox.showerror("Fishbowl Database Login", "Please enter settings for connecting to Fishbowl's database.")
        AskForMySQLLogin()
        return

    imageSaveFolder = filedialog.askdirectory()
    if imageSaveFolder == "":
        return

    warningMsgLines = ["Image exporting will begin after excepting this warning.",
                        "\n\nThis process may last anywhere from several minutes to several hours depending on the number and size on each image.",
                        "You will be notified when finished.",
                        "\n\nWARNING: Any files or directory's in the selected folder will be deleted!",
                        "Please close any currently open files from within the selected folder.",
                        "Any files open here will be forcefully removed and could corrupt if left open.",
                        "\n\nYou have been warned.",
                        "Are you sure you want to continue?"]

    msg = ""
    for line in warningMsgLines:
        if line.startswith("\n"):
            msg = msg.strip()
            msg += line + " "
        else:
            msg += line + " "
    msg.strip()
     
    if not messagebox.askyesno("Image Save", msg, icon="warning"):
        return
    threading.Thread(target=SaveImages).start()
    


#========================================FRAME============================================
mainFrame = Frame(root, bd=1)
mainFrame.pack(pady=10)

AskForMySQLLogin()

#========================================MENUBAR WIDGETS==================================
menubar = Menu(root)
root.config(menu=menubar)

filemenu = Menu(menubar, tearoff=False)
menubar.add_cascade(label="File", menu=filemenu)
filemenu.add_command(label="Set MySQL Credentials", command=AskForMySQLLogin)


#========================================MAIN WIDGETS======================================
progress = Progressbar(mainFrame, orient = HORIZONTAL, length = 400, mode = 'determinate')
button_submit = Button(mainFrame, text="Save All Images", command=ReadAll, relief=RAISED)
button_submit.grid(row=0, column=0, ipadx=90, columnspan=3, pady=10)
label_count = Label(mainFrame, text="0 of 0 Saved.")

label_count.grid(row=9, column=0, columnspan=3)
progress.grid(row=10, column=0, columnspan=3)
    

if __name__ == '__main__':
    root.mainloop()