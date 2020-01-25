import argparse
import time
import json

from datetime import datetime
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.webdriver.chrome.options import Options

def _extract_html(bs_data):
    k = bs_data.find_all(class_="_5pcr userContentWrapper")
    postBigDict = list()

    for item in k:

        # Post Text

        actualPosts = item.find_all(attrs={"data-testid": "post_message"})
        postDict = dict()
        for posts in actualPosts:
            paragraphs = posts.find_all('p')
            text = ""
            for index in range(0, len(paragraphs)):
                text += paragraphs[index].text
            postDict['Post'] = text

        # Links

        postLinks = item.find_all(class_="_6ks")
        postDict['Link'] = ""
        for postLink in postLinks:
            postDict['Link'] = postLink.find('a').get('href')

        # Images

        postPictures = item.find_all(class_="scaledImageFitWidth img")
        postDict['Image'] = ""
        for postPicture in postPictures:
            postDict['Image'] = postPicture.get('src')

        # Post Submit Time

        postSubmits = item.find_all("abbr", class_="_5ptz")
        postDict['PostDate'] = ""
        for postSubmit in postSubmits:
            unix_time_stamp = postSubmit.get("data-utime")
            postDict['PostDate'] = datetime.fromtimestamp(int(unix_time_stamp)).isoformat()

        # Shares
        postShares = item.find_all(attrs={"data-testid": "UFI2SharesCount/root"})
        postDict['Shares'] = ""
        for postShare in postShares:
            postDict['Shares'] = postShare.text.split(" Shares")[0  ]

        # Comments

        postComments = item.find_all(attrs={"data-testid": "UFI2Comment/root_depth_0"})
        postDict['Comments'] = list()

        for comment in postComments:
            comment_tmp = dict()

            if comment.find(class_="_6qw4") is None:
                continue

            comment_username = comment.find(class_="_6qw4").text
            if comment_username is not None:
                comment_tmp["user_nickname"] = comment_username.replace(".", "")

            comment_text = comment.find("span", class_="_3l3x")
            if comment_text is not None:
                comment_tmp["text"] = comment_text.text

            comment_link = comment.find(class_="_ns_")
            if comment_link is not None:
                comment_tmp["link"] = comment_link.get("href")

            comment_pic = comment.find(class_="_2txe")
            if comment_pic is not None:
                comment_tmp["image"] = comment_pic.find(class_="img").get("src")

            comment_timestamp = comment.find("a", class_="_6qw7")
            if comment_timestamp is not None:
                unix_time_stamp = comment_timestamp.find(class_="livetimestamp").get("data-utime")
                comment_tmp["submitted"] = datetime.fromtimestamp(int(unix_time_stamp)).isoformat()

            postDict['Comments'].append(comment_tmp)

        # Reactions

        toolBar = item.find_all(attrs={"role": "toolbar"})

        if not toolBar:  # pretty fun
            continue

        postDict['Reaction'] = dict()

        for toolBar_child in toolBar[0].children:

            str = toolBar_child['data-testid']
            reaction = str.split("UFI2TopReactions/tooltip_")[1]

            postDict['Reaction'][reaction] = 0

            for toolBar_child_child in toolBar_child.children:

                num = toolBar_child_child['aria-label'].split()[0]

                # fix weird ',' happening in some reaction values
                num = num.replace(',', '.')

                if 'K' in num:
                    realNum = float(num[:-1]) * 1000
                else:
                    realNum = float(num)

                postDict['Reaction'][reaction] = realNum

        postBigDict.append(postDict)

    return postBigDict


def extract(browser, page, usage, scrape_comment=False):
    print("__ENTER extract()___")
    print("page = {0}\nusage = {1}\nscrape_comment = {2}\n\n".format(page, usage, scrape_comment))

    # Read in Facebook credentials from file
    with open('facebook_credentials.txt') as file:
        email = file.readline().split('"')[1]
        password = file.readline().split('"')[1]

    # Open facebook.com and log in
    browser.get("http://facebook.com")
    browser.maximize_window()
    browser.find_element_by_name("email").send_keys(email)
    browser.find_element_by_name("pass").send_keys(password)
    browser.find_element_by_id('loginbutton').click()

    # Navigate to the Posts page
    browser.get("http://facebook.com/" + page + "/posts")

    # Test running N times
    N = 10
    for i in range(N):
        # Wait for browser to load data, 5 seconds seems to be enough
        time.sleep(5)
        print("Slept for 5: ", datetime.now())

        # Click on all the comments to scrape them all
        if scrape_comment:
            moreComments = browser.find_elements_by_xpath('//a[@data-testid="UFI2CommentsPagerRenderer/pager_depth_0"]')
            print("Scrolling through to click on more comments")
            while len(moreComments) != 0:
                for moreComment in moreComments:
                    action = webdriver.common.action_chains.ActionChains(browser)
                    try:
                        # move to where the comment button is
                        action.move_to_element_with_offset(moreComment, 5, 5)
                        action.perform()
                        moreComment.click()
                    except:
                        # do nothing right here
                        pass
                moreComments = browser.find_elements_by_xpath('//a[@data-testid="UFI2CommentsPagerRenderer/pager_depth_0"]')

        # Scroll further down until lazy load
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;") 

    # Now that the page scrolled to bottom, grab the source code.
    source_data = browser.page_source

    # Throw the source into BeautifulSoup and parse
    bs_data = bs(source_data, 'html.parser')
    extracted_html = _extract_html(bs_data)

    return extracted_html

# Main execution flow
def main():
    print("__ENTER main()__")

    # Initialize arg parser
    parser = argparse.ArgumentParser(description="Facebook Page Scraper")

    # Specify required args
    required_parser = parser.add_argument_group("required arguments")
    required_parser.add_argument('-page', '-p', help="The Facebook Public Page to scrape", required=True)
    
    # Specify optional args
    optional_parser = parser.add_argument_group("optional arguments")
    optional_parser.add_argument('-usage', '-u', help="What to do with the data: "
                                                      "Print on Screen (PS), "
                                                      "Write to Text File (WT) (Default is WT)", default="WT")
    optional_parser.add_argument('-comments', '-c', help="Scrape ALL Comments of Posts (y/n) (Default is n). When "
                                                         "enabled for pages where there are a lot of comments it can "
                                                         "take a while", default="No")
    # Parse command line args
    args = parser.parse_args()

    # Set comment scraping setting
    scrape_comment = False
    if args.comments == 'y':
        scrape_comment = True

    # Configure webdriver Options
    options = webdriver.ChromeOptions()

    options.add_argument("--disable-infobars")
    options.add_argument("start-maximized")

    # Load image and video blocking Chrome extentions
    options.add_extension('./chrome_extentions/Image_Blocker.crx')
    options.add_extension('./chrome_extentions/Nomovdo_Video_Blocker.crx')

    # Pass the argument 1 to allow and 2 to block
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 1
    })

    # Initilize Browser object
    browser = webdriver.Chrome(executable_path="./chromedriver", options=options)
    
    # Scrape page content
    fb_data = extract(browser=browser, page=args.page, usage=args.usage, scrape_comment=scrape_comment)

    # Write data to file
    if args.usage == "WT":
        with open('fb_data_output.txt', 'w') as file:
            file.write(json.dumps(fb_data, indent=4))
    else:
        for post in fb_data:
            print(post)
            print("\n")

    # Close browser
    browser.close()
    print("Finished")

# Run program
if __name__ == '__main__':
    main()
