母專案連結 https://github.com/se-test-111310514/git-examples/commits/main/
* 分支 https://github.com/se-test-111310514/git-examples/commits/main/

子專案連結 https://github.com/Nickh2k6/git-examples-fork

## 在github上建立新的 organization，名字為 se-test-111310514

## 1. Initial commit 專案的初始存檔
1.在 GitHub 網站上點擊「Create new repository」建立新專案，owner為se-test-111310514
## 2. add gitbranch.md 本地分支開發與合併
1.輸入了 git checkout -b developGitBranch 建立並切換到新分支
2.建立了一個名為 gitBranch.md 的檔案
3.輸入 git add *.md 與 git commit -m "add gitBranch.md" 進行存檔
4.切換回主分支 git checkout main
5.將新分支合併進來 git merge developGitBranch
6.git push origin main 把這筆紀錄推送到github
## 3. add ccckmitFork.md 新增 Fork 練習檔案
1.把自己的專案Fork到我的電腦上
2.新增了一個名為 ccckmitFork.md 的檔案並完成了add commit push
## 4. Merge pull request #1 from Nickh2k6/main 完成 PR 合併
1.利用了自己的帳號 Nickh2k6 的主分支 (main)，向這個總專案發起了一個「合併請求（Pull Request，簡稱 PR）」
2.在 GitHub 網頁上確認程式碼點擊了綠色的「Merge pull request」按鈕，正式把 Nickh2k6 帳號的修改進度，整併到目前的專案中