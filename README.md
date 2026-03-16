# YTU-Online-Class-Automation
🇬🇧 [English (README.md)](README.md)    🇹🇷 [Türkçe (BENI_OKU.tr.md)](BENI_OKU.tr.md)
---

This repo includes an application which let's you automate the joining process to the online classes through the Yildiz Online platform. It essentially is only made for Yildiz Technical University but the same method can be applied to the any other by tweaking with the run_selenium function.

!!! CHROME MUST BE INSTALLED ON YOUR PC !!!

!!! If you're gonna run the code make sure the zoom_join.png is located in the same path as the .py file !!!

Windows defender might ask for permission before running the application. That's because of the pyautogui library I used which helps dedecting the buttons on the screen and clicking on them. 

Usage is pretty simple. You enter your credentials and click on save. Then, you can either assign a class to a certain time of the day and a day of the week, keep the app running in the background; or you can just run the app and click on join now to activate the automation manually.

If you get any error regarding to the undedected libraries, use the function below on your cmd to install each required library one by one

  pip install tkinter
  pip install json
  pip install threading
  pip install datetime
  pip install shelve
  pip install shelve
  pip install os
  pip install sys

  some of these libraries might be already installed but it's best to go one by one to make sure.

I may or may not have added the source code to the repo by the time ur reading this.
