# <img src='./logo.svg' card_color="#FF8600" width="50" style="vertical-align:bottom" style="vertical-align:bottom">CaffeineWiz

Provides the caffeine content of various drinks on request.

## Description

The skill provides the functionality to inform the user of the caffeine content of the requested drink (Multiple drinks in a row are possible)
by collecting the required information from two data sources:

1.  [http://caffeinewiz.com/](http://caffeinewiz.com/) - the main source of information for the drink’s database
2.  [https://www.caffeineinformer.com/the-caffeine-database](https://www.caffeineinformer.com/the-caffeine-database) - secondary source for any non-duplicate drinks
    

CaffeineWiz uses [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) to pull the tables from the websites above, then strips the html tags, and later formats the results into the comprehensive list. That object is pickled for the future use.

The skill will check for updates periodically. You can modify that time period by changing `TIME_TO_CHECK` parameter on top of the file in the init.

## Examples
* "Tell me the caffeine content of Pepsi."
* "How much caffeine is in Starbucks Blonde?"
* "Tell me the caffeine content of Rocket Chocolate."

## Troubleshooting

If you are having trouble finding requested drink or would like to add a new drink to the database,
please feel free to [contact us](https://neongecko.com/ContactUs).

Complete lists of drinks this skill knows can be found at [CaffeineWiz.com](https://caffeinewiz.com) and 
[caffeine informer](https://www.caffeineinformer.com/the-caffeine-database).

## Contact Support

Use the [link](https://neongecko.com/ContactUs) or [submit an issue on GitHub](https://help.github.com/en/articles/creating-an-issue)

## Credits
[NeonGeckoCom](https://github.com/NeonGeckoCom)
[reginaneon](https://github.com/reginaneon)
[NeonDaniel](https://github.com/NeonDaniel)

## Category
**Information**
Daily

## Tags
#NeonGecko Original
#NeonAI
#caffeine
#coffee
