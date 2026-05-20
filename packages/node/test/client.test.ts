import { describe, it, expect } from 'vitest';
import { WjxtConfig } from '../src/config';
import { WjxtError, AuthError, NetworkError, ParseError, SessionExpiredError, DownloadError } from '../src/exceptions';
import { createCrawlStats } from '../src/types';
import {
  encodeGb2312, decodeGb2312,
  extractViewstate, extractHiddenFields,
  isSessionExpired,
  parsePaginationInfo,
  safeFilename, fileHash,
} from '../src/_base';

describe('WjxtConfig', () => {
  it('should create config with defaults', () => {
    const config = new WjxtConfig();
    expect(config.baseUrl).toBe('https://wjxt.gxu.edu.cn');
    expect(config.timeout).toBe(30_000);
    expect(config.autoRelogin).toBe(true);
  });

  it('should merge overrides', () => {
    const config = new WjxtConfig({ username: 'test' });
    const merged = config.mergeWith({ password: 'secret' });
    expect(merged.username).toBe('test');
    expect(merged.password).toBe('secret');
    // original should be unchanged
    expect(config.password).toBe('');
  });

  it('should load from env vars', () => {
    process.env.WJXT_USERNAME = 'envuser';
    const config = WjxtConfig.fromEnv();
    expect(config.username).toBe('envuser');
    delete process.env.WJXT_USERNAME;
  });
});

describe('Exceptions', () => {
  it('should create WjxtError', () => {
    const err = new WjxtError('test error');
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(WjxtError);
    expect(err.message).toBe('test error');
    expect(err.name).toBe('WjxtError');
  });

  it('should create AuthError with cause', () => {
    const cause = new Error('underlying');
    const err = new AuthError('login failed', cause);
    expect(err).toBeInstanceOf(WjxtError);
    expect(err).toBeInstanceOf(AuthError);
    expect(err.cause).toBe(cause);
  });

  it('should have correct inheritance chain for all exceptions', () => {
    expect(new NetworkError('')).toBeInstanceOf(WjxtError);
    expect(new ParseError('')).toBeInstanceOf(WjxtError);
    expect(new SessionExpiredError('')).toBeInstanceOf(WjxtError);
    expect(new DownloadError('')).toBeInstanceOf(WjxtError);
  });
});

describe('Base utilities', () => {
  it('should encode GB2312', () => {
    const encoded = encodeGb2312('全部文件');
    expect(encoded).toBeTruthy();
    expect(encoded.startsWith('%')).toBe(true);
  });

  it('should decode GB2312 roundtrip', () => {
    const original = '学工部';
    const encoded = encodeGb2312(original);
    const decoded = decodeGb2312(encoded);
    expect(decoded).toBe(original);
  });

  it('should extract VIEWSTATE from ASP.NET HTML', () => {
    const html = '<input type="hidden" name="__VIEWSTATE" value="abc123" />';
    const fields = extractViewstate(html);
    expect(fields['__VIEWSTATE']).toBe('abc123');
  });

  it('should extract hidden fields', () => {
    const html = '<input type="hidden" name="myField" value="myValue" />';
    const fields = extractHiddenFields(html);
    expect(fields['myField']).toBe('myValue');
  });

  it('should detect session expired (short HTML with redirect)', () => {
    const expiredHtml = 'window.location="default.aspx"请重新登录';
    expect(isSessionExpired(expiredHtml)).toBe(true);
  });

  it('should not flag long normal HTML as expired', () => {
    const normalHtml = '<html><body>' + 'x'.repeat(1000) + '</body></html>';
    expect(isSessionExpired(normalHtml)).toBe(false);
  });

  it('should parse pagination info', () => {
    const html = '第3页/总10 页 每页50条/共482条';
    const info = parsePaginationInfo(html);
    expect(info.currentPage).toBe(3);
    expect(info.totalPages).toBe(10);
    expect(info.perPage).toBe(50);
    expect(info.totalItems).toBe(482);
  });

  it('should return defaults for missing pagination', () => {
    const info = parsePaginationInfo('no match');
    expect(info.currentPage).toBe(1);
    expect(info.totalPages).toBe(1);
    expect(info.perPage).toBe(50);
    expect(info.totalItems).toBe(0);
  });

  it('should create safe filenames', () => {
    expect(safeFilename('test')).toBe('test');
    expect(safeFilename('a<b>c')).toBe('a_b_c');
    expect(safeFilename('')).toBe('unnamed');
  });

  it('should generate deterministic file hash', () => {
    const hash = fileHash(12345);
    expect(hash).toBeTruthy();
    expect(hash).toBe(fileHash(12345));
    expect(hash).not.toBe(fileHash(12346));
  });
});

describe('CrawlStats', () => {
  it('should create zero-initialized stats', () => {
    const stats = createCrawlStats();
    expect(stats.totalFiles).toBe(0);
    expect(stats.downloaded).toBe(0);
    expect(stats.skipped).toBe(0);
    expect(stats.noAttachment).toBe(0);
    expect(stats.failed).toBe(0);
  });
});
