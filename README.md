# ![](https://0000.us/klatchat/app/files/neon_images/icons/neon_paw.png)CaffeineWiz

# Summary

Provides the caffeine content of various drinks on request. Multiple drinks in a row are possible.

# Requirements

No special required packages for this skill.

# Description

The skill provides the functionality to inform the user of the caffeine content of the requested drink by collecting the required information from two data sources:

1.  [http://caffeinewiz.com/](http://caffeinewiz.com/) - the main source of information for the drink’s database
2.  [https://www.caffeineinformer.com/the-caffeine-database](https://www.caffeineinformer.com/the-caffeine-database) - secondary source for any non-duplicate drinks
    

CaffeineWiz uses [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) to pull the tables from the websites above, then strips the html tags, and later formats the results into the comprehensive list. That object is pickled for the future use.

The skill will check for updates periodically. You can modify that time period by changing `TIME_TO_CHECK` parameter on top of the file in the init.

# How to Use

First, make your request:

Say `“Hey Neon”` if you are in the wake words mode. Make sure to follow the pattern of `"how much caffeine is in"` or `"tell me caffeine content of"` and add your desired drink name.

For example:

-   tell me caffeine content of pepsi
    
-   how much caffeine is in starbucks blonde
    
-   tell me caffeine content of rocket chocolate
    

Wait for Neon to reply with the information about your requested drink. The reply will come in the format of `The drink {{drink}} has {{caffeine_content}} milligrams of caffeine in {{drink_size}} ounces. Provided by CaffeineWiz.`

If more than one drink is available, or more than one drink was a match, Neon will offer to read them all back to you by saying `I have more drinks that match. Would you like to hear them?` And, in addition to the phrase above, the original sentence will say `The best match is`

If you have wake words turned on, Neon will ask you to `Say how about caffeine content of another drink or say goodbye.`; if you are skipping wake words, Neon will end the conversation by saying `Stay caffeinated!`

  

# Location

    ${skills}/CaffeineWiz.neon

# Files

 <details>
<summary>Click to expand.</summary>
<br>   

        ${skills}/CaffeineWiz.neon/drinkList_from_caffeine_informer.txt  
        ${skills}/CaffeineWiz.neon/drinkList_from_caffeine_wiz.txt  
        ${skills}/CaffeineWiz.neon/__init__.py  
        ${skills}/CaffeineWiz.neon/README.md  
        ${skills}/CaffeineWiz.neon/settings.json  
        ${skills}/CaffeineWiz.neon/test/intent  
        ${skills}/CaffeineWiz.neon/dialog/en-us  
        ${skills}/CaffeineWiz.neon/test  
        ${skills}/CaffeineWiz.neon/vocab/en-us/Neon.voc  
        ${skills}/CaffeineWiz.neon/regex/en-us  
        ${skills}/CaffeineWiz.neon/dialog/de-de  
        ${skills}/CaffeineWiz.neon/vocab/en-us/YesIDo.voc  
        ${skills}/CaffeineWiz.neon/test/intent/001.CaffeineContentIntent.intent.json  
        ${skills}/CaffeineWiz.neon/vocab/de-de/CaffeineKeyword.voc  
        ${skills}/CaffeineWiz.neon/dialog/de-de/drink.caffeine.dialog  
        ${skills}/CaffeineWiz.neon/vocab/en-us/UpdateCaffeine.voc  
        ${skills}/CaffeineWiz.neon/dialog  
        ${skills}/CaffeineWiz.neon/vocab/en-us  
        ${skills}/CaffeineWiz.neon/vocab  
        ${skills}/CaffeineWiz.neon/test/intent/004.NoIntent.intent.json  
        ${skills}/CaffeineWiz.neon/regex  
        ${skills}/CaffeineWiz.neon/vocab/de-de  
        ${skills}/CaffeineWiz.neon/regex/de-de  
        ${skills}/CaffeineWiz.neon/vocab/en-us/CaffeineKeyword.voc  
        ${skills}/CaffeineWiz.neon/vocab/de-de/GoodbyeKeyword.voc  
        ${skills}/CaffeineWiz.neon/vocab/en-us/GoodbyeKeyword.voc  
        ${skills}/CaffeineWiz.neon/test/intent/003.YesIDoIntent.intent.json  
        ${skills}/CaffeineWiz.neon/dialog/en-us/drink.caffeine.dialog  
        ${skills}/CaffeineWiz.neon/test/intent/002.CaffeineContentGoodbyeIntent.intent.json  
        ${skills}/CaffeineWiz.neon/vocab/en-us/NoIntent.voc  
        ${skills}/CaffeineWiz.neon/regex/de-de/drink.rx  
        ${skills}/CaffeineWiz.neon/regex/en-us/drink.rx

</details> 

# Class Diagram

[Click Here](https://0000.us/klatchat/app/files/neon_images/class_diagrams/CaffeineWiz.png)

# Available Intents
<details>
<summary>Click to expand.</summary>
<br>

### GoodbyeKeyword.voc

    goodbye  
    that's all  
    we're done

### UpdateCaffeine.voc

    update caffeine wiz database  
    update caffeine database

### Neon.voc

    neon  
    leon  
    nyan

### NoIntent.voc

    no i do not  
    no  
    not now  
    i am done  
    nevermind

### CaffeineKeyword.voc

    tell me caffeine content of  
    how much caffeine is  in  
    how about caffeine content of  
    how much caffeine in

  

### YesIDo.voc

    yes i do  
    i do  
    i would  
    yes i would  
    yes

### GoodbyeKeyword.voc

    Auf Wiedersehen  
    bye  
    das wars  
    ende  
    end  
    Wir sind fertig

  

### CaffeineKeyword.voc

    koffein

</details> 

# Examples

### Text

    Tell me caffeine content of *drink*? / how much caffeine is  in *drink*?  
    >> The drink {{drink}} has {{caffeine_content}} milligrams of caffeine in {{drink_size}} ounces. Provided by CaffeineWiz. Say how about caffeine content of another drink or say goodbye.  
    Goodbye / that's all / we're done  
        - Goodbye. Stay caffeinated!

or -

    How about caffeine content of *drink*?  
    >> The drink {{drink}} has {{caffeine_content}} milligrams of caffeine in {{drink_size}} ounces. Provided by CaffeineWiz. I have more drinks that match. Would you like to hear them?  
    No.  
    >> Stay caffeinated!

  

### Picture

### Video

  

# Troubleshooting

If you are having trouble finding requested drink, would like to add a new drink to the database, or got a "I am sorry, " + drink + " is not on my list. Let my creators know and they will teach me new information!" from Neon, please feel free to [contact us](https://neongecko.com/ContactUs)

  

# Contact Support

Use the [link](https://neongecko.com/ContactUs) or [submit an issue on GitHub](https://help.github.com/en/articles/creating-an-issue)

# Credits

reginaneon [neongeckocom](https://neongecko.com/)

