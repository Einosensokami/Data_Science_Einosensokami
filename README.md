# 資料科學期中報告：第 1～6、8～14、17 題

各題各自放在一個資料夾，程式都從網站抓取資料。執行完成後，輸出檔會產生在對應題目的資料夾內。

## 安裝套件

在專案根目錄執行：

```bash
python -m pip install -r requirements.txt
```

## 題目與輸出

1. `第1題_本週新片`：開眼電影網本週新片，輸出 `movies.csv`
2. `第2題_台銀牌價`：臺灣銀行最新牌告匯率，輸出 `bank.csv`
3. `第3題_腸病毒資料`：政府資料開放平臺腸病毒資料，輸出 `NHI_EnteroviralInfection.csv`
4. `第4題_博客來書籍`：博客來「演算法」書籍資料，輸出 `booklist.csv`
5. `第5題_電影票房排行榜`：開眼電影網台北週末票房，輸出 `Taipei_movies.csv`
6. `第6題_NBA球隊運動員`：CLE、HOU、GSW 的 2023–24 球季球員資料，輸出 `players.csv`
7. `第8題_近期上映強片`：開眼電影網近期上映推薦，輸出 `movies.csv`
8. `第9題_Google新聞`：Selenium 抓取 Google 新聞首頁各分類標題，輸出 `google_news.csv` 與 `google_news.txt`
9. `第10題_PTT八卦板`：Selenium 點選成年確認，列出網頁 title 與文章列表，輸出 `gossiping.csv` 與 `gossiping.txt`
10. `第11題_NBA商品資料`：Selenium 操作商品分頁，逐頁輸出 `NBA_Products1.csv` 至 `NBA_ProductsN.csv`
11. `第12題_Steam遊戲推薦`：Selenium 操作 Google 搜尋「Steam 遊戲推薦」，輸出 `steam_games.csv`
12. `第13題_momo搜尋頁`：Selenium 自動在 momo 搜尋「nba」，輸出 `NBA_test.html`
13. `第14題_NBA球員薪水`：Selenium 逐頁抓取 HoopsHype 球員薪資，輸出 `highest.csv` 與 `all_play.csv`
14. `第17題_GitHub網頁資料`：Selenium 自動登入 GitHub，擷取附圖兩個提示區塊，輸出 `github_windows.csv` 與 `github_dashboard.png`

第 1～3 題可在專案根目錄執行對應指令：

```powershell
python "第1題_本週新片/main.py"
python "第2題_台銀牌價/main.py"
python "第3題_腸病毒資料/main.py"
```

## 第 4 題：博客來書籍資料

第 4 題搜尋博客來關鍵字「演算法」。每抓一頁就開啟一個新的可見 Chrome，載入包含該頁碼的搜尋結果網址；抓完後關閉瀏覽器，再以新的瀏覽器處理下一頁。

每頁會解析以下資料，跨頁去重後寫入 `第4題_博客來書籍/booklist.csv`：

- 書名
- 網址
- 作者
- 書價

在專案根目錄執行：

```powershell
python "第4題_博客來書籍/main.py"
```

執行時可看到每一頁各自開啟及關閉 Chrome。遇到下列情況時會停止：

- 頁面沒有商品
- 頁面內容全部重複
- 某頁筆數少於第一頁，代表已到最後一頁
- 博客來顯示「連線暫時異常」

若博客來顯示「連線暫時異常」，程式不會覆蓋既有的 CSV。請間隔一段時間後再執行，不要立即連續重試。

## 第 5 題：電影票房排行榜

第 5 題以 Selenium 開啟開眼電影網的「本週新片」頁，並模擬滑鼠操作：

1. 移入「電影」選單後，點選「票房排行榜」
2. 在台北週末票房排行榜點選 `more`
3. 將完整 20 筆排行輸出至 `第5題_電影票房排行榜/Taipei_movies.csv`

CSV 欄位為：排名、片名、本週票房、累計票房。

在專案根目錄執行：

```powershell
python "第5題_電影票房排行榜/main.py"
```

## 第 6 題：NBA 球隊運動員資料

使用 requests 抓取 Basketball Reference 三隊的 `2024.html`，再以 BeautifulSoup 解析「Roster and Stats」頁面的 Roster 球員名單。網址中的 2024 指 2023–24 球季。

在專案根目錄執行：

```powershell
python "第6題_NBA球隊運動員/main.py"
```

CSV 欄位為：球隊、背號、姓名、位置、體重、生日、經驗、大學。

- 球隊使用 `CLE`、`HOU`、`GSW` 代碼；體重保留網站的磅（lb）單位。
- 經驗為該球季開始前的 NBA/ABA 年資，`R` 表示新人；網站沒有大學資料時保留空白。
- 背號保留原文（例如 `00` 或同季多個背號）；若使用 Excel，請將背號欄以文字匯入以保留前導零。
- 輸出檔名為 `players.csv`，採 UTF-8 BOM 編碼。
- 三隊全部抓取成功後才輸出；連線失敗或找不到表格時停止，保留既有 CSV。

## 第 8 題：近期上映強片

使用 requests 與 BeautifulSoup，抓取開眼電影網[近期上映頁面](https://www.atmovies.com.tw/movie/next/)中「近期上映推薦」的全部電影。這是題目本週新片頁導覽列中的「近期上映」入口；依補充筆記，以目前的推薦區塊對應題目「近期上映強片」。範圍為推薦清單，不包含各週完整上映名單或側欄下拉選單。

在專案根目錄執行：

```powershell
python "第8題_近期上映強片/main.py"
```

程式逐筆列印名稱、上映時間及完整連結網址，並存至該題資料夾的 `movies.csv`。日期統一為 `YYYY/MM/DD`，CSV 使用 UTF-8 BOM，方便 Excel 顯示中文。上映日期依網站公告保留，不自行限制日期範圍；網站連線失敗、清單為空或必要欄位缺漏時，停止並保留既有 CSV。

## 第 9 題：Google 新聞

使用 Selenium 開啟 [Google 新聞臺灣繁體中文首頁](https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant)，列印網頁 title，並自動捲動至頁面高度與新聞連結數穩定後，輸出以下區塊內的全部新聞標題：

- 焦點提要下的「焦點新聞」與「地方新聞」
- 您的主題（包含各子主題的新聞）
- 更多新聞

```powershell
python "第9題_Google新聞/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器，加入 `--headless` 可在背景執行。程式依區塊標題定位，不依賴新聞的固定筆數；每個分類內依網址去重，同一則新聞若屬於不同分類會分別保留。

輸出至該題資料夾：`google_news.csv`（分類、標題、網址）與 `google_news.txt`（網頁標題及分類新聞清單），均採 UTF-8 BOM 編碼。抓取範圍是本次首頁載入的各區塊，不包含點入分類後的其他頁面或整個新聞資料庫。地方新聞依網站偵測地區而異，個人化及版面也可能影響內容；缺少分類時會明確提示「部分完成」，不將其他分類的新聞冒充缺少的內容。連線失敗或完全無法解析時保留既有輸出。

## 第 10 題：PTT Gossiping

使用 Selenium 開啟 [PTT 八卦板](https://www.ptt.cc/bbs/Gossiping/index.html)，點選「我同意，我已年滿十八歲」的進入按鈕，並確認網站已設定 `over18=1` Cookie。進入後列印實際網頁 title，以及本頁每篇文章的網址、標題、作者。

```powershell
python "第10題_PTT八卦板/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器，加入 `--headless` 可在背景執行。

抓取範圍為目前索引頁，包含置底公告；已刪除且沒有連結的文章會略過。網址輸出為 `https://www.ptt.cc/bbs/Gossiping/...` 完整網址，可直接貼到 Chrome 開啟；首次開啟時可能需要點選成年確認。網頁 title 保留網站原文，可能包含看板名稱。

輸出至該題資料夾：`gossiping.csv`（網址、標題、作者）與 `gossiping.txt`（網頁標題及逐篇文章清單），均使用 UTF-8 BOM 編碼。每次執行抓取當時的文章；分級確認失敗、連線失敗或無法解析文章時，停止並保留既有輸出。

## 第 11 題：NBA 商品資料

使用 Selenium 開啟 [NBA 商品資料頁](https://fchart.github.io/ML/nba_items.html)，讀取目前表格後操作「下一頁」，直到最後一頁。程式依頁面實際產生的分頁按鈕判斷頁數，不將頁數寫死。

```powershell
python "第11題_NBA商品資料/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器，加入 `--headless` 可在背景執行。

每頁分別輸出 `NBA_Products1.csv`、`NBA_Products2.csv`，依此類推；欄位為商品編號、商品名稱、價格。每完成一個檔案會列印 `儲存頁面: 頁碼`。CSV 使用 UTF-8 BOM 編碼，可直接以 Excel 開啟而不會出現中文亂碼。

程式先成功收集全部頁面，才覆蓋輸出檔；若連線、分頁切換或資料結構發生錯誤，會停止並保留既有 CSV。本次頁數少於上次執行時，也會刪除已不屬於目前資料的較高頁碼輸出檔。

## 第 12 題：Steam 遊戲推薦

使用 Selenium 與 WebDriver 開啟 Google 首頁，在搜尋框自動輸入「Steam 遊戲推薦」並送出，列印第一頁搜尋區中的結果標題及完整連結，依網址去重後存成 `第12題_Steam遊戲推薦/steam_games.csv`。

```powershell
python "第12題_Steam遊戲推薦/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器；若 Google 顯示真人驗證，請在 Chrome 視窗中手動完成，程式最多等待 5 分鐘後繼續擷取。加入 `--headless` 可在背景執行，但遇到真人驗證時會停止並提示改用可見模式。

CSV 欄位為「標題、網址」，使用 UTF-8 BOM 編碼，方便 Excel 顯示中文。網址為可直接開啟的 HTTP(S) 連結；Google `/url` 轉址會取出查詢參數中的目標網址，`/goto` 轉址則以 requests 讀取 HTTP Location。搜尋輸入及結果擷取均由 Selenium 完成。範圍為第一頁搜尋結果，不包含其他分頁；搜尋結果會隨時間、地區與 Google 版面改變。連線失敗、驗證逾時、轉址解析失敗或沒有有效結果時，不覆蓋既有 CSV。

## 第 13 題：momo 搜尋頁

使用 Selenium 開啟 momo 首頁，自動在搜尋框輸入 `nba` 並按 Enter。等待搜尋結果的商品出現後，將第一頁已渲染的 HTML 存為 `第13題_momo搜尋頁/NBA_test.html`。

```powershell
python "第13題_momo搜尋頁/main.py"
```

需要已安裝 Chrome；Selenium 自動管理 WebDriver。預設開啟可見瀏覽器，加入 `--headless` 可在背景執行。程式會列印搜尋結果網址及本頁商品筆數；搜尋失敗、逾時或商品尚未載入時，不覆蓋既有 HTML。

`NBA_test.html` 採 UTF-8 編碼，可用 Chrome 開啟。保存的是當次第一頁的靜態畫面，會移除動態腳本以避免本機開啟時重新渲染，並加入原始網址作為相對路徑的基準。商品文字保留在 HTML 內，樣式及圖片仍需網路載入；搜尋、分頁等互動功能請使用原始網站。

## 第 14 題：NBA 球員薪水

使用 Selenium 開啟 [HoopsHype 球員薪資頁](https://hoopshype.com/salaries/players/)，逐一切換表格分頁，並以 BeautifulSoup 解析全部列。再開啟薪資排名前三位球員的個人頁，讀取背號。

```powershell
python "第14題_NBA球員薪水/main.py"
```

需要已安裝 Chrome；加入 `--headless` 可在背景執行。輸出均位於第 14 題資料夾，使用 UTF-8 BOM 編碼：

- `highest.csv`：前三位球員的名字、背號及當前顯示球季的薪資。
- `all_play.csv`：表格各頁的全部列，包含排名、球員與所有顯示的球季薪資欄位。

球季與資料筆數以執行當時網站顯示為準。網站若對同一球員列出多筆不同薪資，`all_play.csv` 會原樣保留；沒有個人頁連結的球員也會保留在表格資料中。抓取失敗時不會覆蓋既有 CSV。

## 第 17 題：GitHub 網頁資料

在專案根目錄執行：

```powershell
python "第17題_GitHub網頁資料/main.py"
```

依提示輸入 GitHub 帳號與密碼（密碼輸入時會顯示，方便核對）。也可事先設定 `GITHUB_USERNAME`、`GITHUB_PASSWORD` 環境變數。程式會開啟可見 Chrome，自動填入登入表單並按下 Sign in；表單中的隱藏 `authenticity_token` 由瀏覽器正常提交，無須自行取得或硬編碼。

若出現二階段驗證、裝置驗證或其他互動驗證，請在瀏覽器內完成，程式最多等待 5 分鐘。GitHub 的驗證流程見[官方說明](https://docs.github.com/en/authentication/securing-your-account-and-data-secure/verifying-new-devices-when-signing-in)。

登入後首頁目前的主要內容區塊為：

| 區域 | 標題 | 擷取內容 |
| --- | --- | --- |
| 左欄 | Top repositories | 顯示的 repository 名稱與連結 |
| 中欄 | Feed | 每筆首頁動態的文字與第一個連結 |

登入後程式擷取這兩個區塊、列印結果，並在第 17 題資料夾產生：

- `github_dashboard.csv`：區域、項目、內容、連結、頁面網址、狀態，採 UTF-8 BOM 編碼供 Excel 開啟。
- `github_dashboard.png`：登入後目前畫面的截圖，供比對題目與報告使用。

GitHub 首頁會依帳號與當下活動而改變。程式找不到左欄或中欄時，會將 CSV 狀態標為「未顯示」；找到標題但沒有資料時則標為「找到標題但無 repository／動態」。

程式不儲存密碼、Cookie 或原始登入 HTML。CSV 與截圖可能含個人資料，已加入 `.gitignore`。執行需要已安裝 Chrome；Selenium 會管理對應的 WebDriver。
