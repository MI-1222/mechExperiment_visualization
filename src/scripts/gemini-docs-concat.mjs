// node src/scripts/gemini-docs-concat.mjs

import fs from 'fs';
import path from 'path';

/**
 * 指定されたディレクトリ内のmdファイルを再帰的に検索し、そのパスのリストを返す。
 * @param {string} dir - 検索を開始するディレクトリのパス
 * @returns {string[]} mdファイルのパスの配列
 */
function findMdFiles(dir) {
  let mdFiles = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // サブディレクトリの場合、再帰的に検索
      mdFiles = mdFiles.concat(findMdFiles(fullPath));
    } else if (path.extname(entry.name).toLowerCase() === '.md') {
      // ファイルが.mdで終わる場合、リストに追加
      mdFiles.push(fullPath);
    }
  }
  return mdFiles;
}

/**
 * mdファイルを結合して1つのファイルに保存する。
 * @param {string} inputDir - 探索対象のディレクトリ
 * @param {string} outputFile - 出力先のファイルパス
 */
function mergeMdFiles(inputDir, outputFile) {
  console.log(`Searching for .md files in "${inputDir}"...`);

  try {
    // 1. mdファイルのリストを取得
    let mdFilePaths = findMdFiles(inputDir).reverse();
    // 配列の先頭にREADME.mdを追加
    mdFilePaths.unshift('README.md');

    if (mdFilePaths.length === 0) {
      console.log('No .md files found.');
      return;
    }

    console.log('Found files:');
    mdFilePaths.forEach(file => console.log(`- ${file}`));

    // 2. 各ファイルの内容を読み込んで結合
    const combinedContent = mdFilePaths
      .map(filePath => {
        // 各ファイルの内容を読み込む
        return fs.readFileSync(filePath, 'utf8');
      })
      // 各ファイルの内容の間に水平線と改行を2つ入れて区切る
      .join('\n\n---\n\n');

    // 3. 結合した内容を指定されたファイルに書き込む（上書き保存）
    fs.writeFileSync(outputFile, combinedContent, 'utf8');

    console.log(`\n✅ Successfully merged ${mdFilePaths.length} files into "${outputFile}"!`);

  } catch (error) {
    console.error('An error occurred:', error.message);
  }
}

// --- 実行設定 ---
// 探索を開始するフォルダを指定
const inputDirectory = 'docs'; 
// 出力するファイル名を指定
const outputFilePath = 'GEMINI.md'; 

// スクリプトを実行
mergeMdFiles(inputDirectory, outputFilePath);
