const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

let events = [];
let currentIndex = -1;
let decorationType;
let statusBarItem;
let playTimer = null;
let lastEditor = null;

function activate(context) {
  decorationType = vscode.window.createTextEditorDecorationType({
    backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
    isWholeLine: true
  });

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  context.subscriptions.push(statusBarItem);

  context.subscriptions.push(
    vscode.commands.registerCommand('codeTracer.loadLatest', loadLatestTrace),
    vscode.commands.registerCommand('codeTracer.stepForward', () => step(1)),
    vscode.commands.registerCommand('codeTracer.stepBack', () => step(-1)),
    vscode.commands.registerCommand('codeTracer.togglePlay', togglePlay)
  );
}

function findLatestTrace() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders) return null;
  const dir = path.join(folders[0].uri.fsPath, '.traces');
  if (!fs.existsSync(dir)) return null;
  const files = fs.readdirSync(dir)
    .filter(f => f.endsWith('.ndjson'))
    .map(f => ({ f, t: fs.statSync(path.join(dir, f)).mtimeMs }))
    .sort((a, b) => b.t - a.t);
  return files.length ? path.join(dir, files[0].f) : null;
}

async function loadLatestTrace() {
  const file = findLatestTrace();
  if (!file) {
    vscode.window.showWarningMessage('No trace files found in .traces');
    return false;
  }
  const lines = fs.readFileSync(file, 'utf-8').split('\n').filter(Boolean);
  events = [];
  for (const line of lines.slice(1)) { // skip header line
    const ev = JSON.parse(line);
    if (ev[0] === 'line') {
      events.push({ file: ev[2], line: ev[1], vars: ev[4] || {} });
    }
  }
  currentIndex = -1;
  statusBarItem.show();
  return true;
}

async function step(direction) {
  if (!events.length) {
    const ok = await loadLatestTrace();
    if (!ok || !events.length) return;
  }
  const next = currentIndex + direction;
  if (next < 0 || next >= events.length) return;
  currentIndex = next;
  await highlightCurrent();
}

async function highlightCurrent() {
  const ev = events[currentIndex];
  let doc;
  try {
    doc = await vscode.workspace.openTextDocument(vscode.Uri.file(ev.file));
  } catch (e) {
    return;
  }

  const editor = await vscode.window.showTextDocument(doc, { preview: false, preserveFocus: false });

  if (lastEditor && lastEditor !== editor) {
    lastEditor.setDecorations(decorationType, []);
  }
  lastEditor = editor;

  const lineIndex = ev.line - 1;
  if (lineIndex < 0 || lineIndex >= doc.lineCount) return;

  const range = doc.lineAt(lineIndex).range;
  const deco = {
    range,
    renderOptions: {
      after: {
        contentText: inlineVars(ev.vars),
        color: new vscode.ThemeColor('editorCodeLens.foreground'),
        fontStyle: 'italic',
        margin: '0 0 0 2em'
      }
    },
    hoverMessage: hoverVars(ev.vars)
  };
  editor.setDecorations(decorationType, [deco]);
  editor.revealRange(range, vscode.TextEditorRevealType.InCenter);

  const count = Object.keys(ev.vars).length;
  statusBarItem.text = `Trace ${currentIndex + 1}/${events.length}: ${path.basename(ev.file)}:${ev.line} (${count} vars)`;
}

const INLINE_MAX = 100;

function inlineVars(vars) {
  const keys = Object.keys(vars);
  if (!keys.length) return '';
  let parts = [];
  let len = 0;
  for (const k of keys) {
    const piece = `${k}=${vars[k]}`;
    if (len + piece.length > INLINE_MAX) {
      parts.push(`… +${keys.length - parts.length} more`);
      break;
    }
    parts.push(piece);
    len += piece.length + 2;
  }
  return '  ' + parts.join(', ');
}

function hoverVars(vars) {
  const keys = Object.keys(vars);
  if (!keys.length) return undefined;
  const md = new vscode.MarkdownString();
  md.appendMarkdown(`**${keys.length} variable${keys.length === 1 ? '' : 's'}**\n\n`);
  const body = keys.map(k => `${k} = ${vars[k]}`).join('\n');
  md.appendCodeblock(body, 'python');
  md.isTrusted = true;
  return md;
}

function togglePlay() {
  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
    return;
  }
  playTimer = setInterval(() => {
    if (currentIndex + 1 >= events.length) {
      clearInterval(playTimer);
      playTimer = null;
      return;
    }
    step(1);
  }, 300);
}

function deactivate() {
  if (playTimer) clearInterval(playTimer);
}

module.exports = { activate, deactivate };
