import asyncpg
import json
import os
import re
from datetime import datetime
import httpx
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import sys

load_dotenv()

router = APIRouter()
DATABASE_URL = os.getenv("POSTGRES_CONNECTION_URL")

MAGAZINE_IFRAME_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0, viewport-fit=cover"
    />
    <title>Magazine Flipbook Viewer</title>

    <!-- PDF.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>

    <!-- PageFlip (flip.js) - CSS styles are embedded inline below -->
    <script src="https://cdn.jsdelivr.net/npm/page-flip/dist/js/page-flip.browser.min.js"></script>

    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #1a1a1a;
            overflow: hidden;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        #flipbook-container {
            flex: 1;
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            perspective: 2000px;
            overflow: hidden;
            min-height: 400px;
        }

        .flipbook {
            position: relative;
            display: block;
            width: 100%;
            height: 100%;
            margin-top: 0rem; /* Default for iframe mode */
        }

        /* PageFlip page content */
        .page {
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.2);
            cursor: pointer;
        }

        .page .page-content {
            position: relative;
            width: 100%;
            height: 100%;
        }

        .page canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        /* Make the leading blank page transparent (no white panel on the left) */
        .page[data-blank="true"] {
            background: transparent;
            box-shadow: none;
            cursor: default;
        }

        /* Navigation Arrows */
        .nav-arrow {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: none; /* shown by JS */
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            user-select: none;
        }

        .nav-arrow:hover { background: white; }

        .nav-arrow.prev { left: 20px; }
        .nav-arrow.next { right: 20px; }

        .nav-arrow svg { width: 24px; height: 24px; fill: #333; }

        .nav-arrow.disabled { opacity: 0.3; cursor: not-allowed; }

        /* Hide navigation arrows on small screens */
        @media (max-width: 768px) {
            .nav-arrow { display: none !important; }
        }

        /* Controls Bar */
        #controls {
            position: absolute;
            bottom: 0;
            left: 0; right: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(10px);
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            z-index: 1500;
        }

        /* Progress Bar */
        .progress-container {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .page-info {
            color: white;
            font-size: 14px;
            min-width: 80px;
            text-align: center;
        }

        .progress-bar {
            flex: 1;
            height: 4px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
            position: relative;
            cursor: pointer;
        }

        .progress-fill {
            height: 100%;
            background: #007bff;
            border-radius: 2px;
            position: relative;
            transition: width 0.3s ease;
        }

        .progress-thumb {
            position: absolute;
            top: 50%;
            right: -8px;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            background: white;
            border-radius: 50%;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            cursor: grab;
        }
        .progress-thumb:active { cursor: grabbing; }

        /* Control Buttons */
        .control-btn {
            background: transparent;
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        .control-btn:hover {
            background: rgba(255,255,255,0.1);
            border-color: rgba(255,255,255,0.5);
        }
        .control-btn svg { width: 18px; height: 18px; fill: white; }

        /* Mobile: icon-only control buttons in controls bar */
        @media (max-width: 768px) {
            #controls .control-btn span { display: none !important; }
            #controls .control-btn { padding: 8px; gap: 0; }
        }

        /* URL Highlights */
        .url-overlay {
            position: absolute;
            border: 1px solid #007bff;
            background: rgba(0,123,255,0.2);
            cursor: pointer;
            transition: all 0.2s ease;
            pointer-events: all;
            border-radius: 5px;
            z-index: 50; /* above canvas, inside page-content */
            min-width: 20px;
            min-height: 14px;
        }
        .url-overlay:hover {
            background: rgba(0,123,255,0.6);
            box-shadow: 0 0 20px rgba(0,123,255,1);
            border-color: #0056b3;
            border-width: 4px;
            transform: scale(1.05);
        }
        .url-overlay::after {
            content: "🔗 CLICK";
            position: absolute;
            top: -25px;
            left: 50%;
            transform: translateX(-50%);
            background: #007bff;
            color: white;
            padding: 2px 6px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.2s ease;
            pointer-events: none;
        }
        .url-overlay:hover::after { opacity: 1; }

        /* Responsive for iframe vs fullscreen */
        body.iframe-mode #flipbook-container { padding: 10px 10px 70px 10px; /* Extra bottom padding for controls */ }
        body.fullscreen-mode { background: #000; }
        body.fullscreen-mode #flipbook-container { padding: 40px; }
        body.fullscreen-mode .flipbook { margin-top: 0rem; /* Different margin for fullscreen */ }

        /* Fullscreen specific styles */
        :-webkit-full-screen { background: #000; }
        :-moz-full-screen { background: #000; }
        :fullscreen { background: #000; }

        /* Loading indicator */
        .page-loading {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            display: flex; flex-direction: column; align-items: center; gap: 10px;
            z-index: 2000;
        }
        .page-loading .spinner {
            width: 40px; height: 40px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-top: 3px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg);} 100% { transform: rotate(360deg);} }
        .page-loading .text { color: rgba(255,255,255,0.8); font-size: 14px; }

        /* Hide controls in loading state */
        body.loading #controls { opacity: 0.5; pointer-events: none; }

        /* Toast Notification */
        .toast-notification {
            position: fixed;
            bottom: -100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 123, 255, 0.95);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 3000;
            transition: bottom 0.3s ease;
            font-size: 14px;
            font-weight: 500;
        }
        .toast-notification.show {
            bottom: 20px;
        }
        .toast-notification svg {
            width: 20px;
            height: 20px;
            fill: white;
        }
        @media (max-width: 768px) {
            .toast-notification {
                bottom: -100px;
                left: 10px;
                right: 10px;
                transform: none;
                font-size: 13px;
                padding: 10px 16px;
            }
            .toast-notification.show {
                bottom: 10px;
            }
        }

        /* Download Form Modal */
        .download-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 5000;
            backdrop-filter: blur(4px);
        }
        .download-modal-overlay.show {
            display: flex;
        }
        .download-modal {
            background: #FBFAF7;
            border-radius: 16px;
            padding: 24px;
            max-width: 520px;
            width: 90%;
            position: relative;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease;
        }
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .download-modal-close {
            position: absolute;
            top: 5px;
            right: 5px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #5f6368;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s ease;
        }
        .download-modal-close:hover {
            background: rgba(0, 0, 0, 0.05);
            color: #1A1A1A;
        }
        .download-modal h2 {
            font-family: 'Lexend', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: #1A1A1A;
            margin: 0 0 20px 0;
        }
        .download-form-row {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
        }
        .download-form-field {
            flex: 1;
            position: relative;
        }
        .download-form-field.full-width {
            width: 100%;
        }
        .download-form-field label {
            position: absolute;
            top: 12px;
            left: 16px;
            font-size: 14px;
            color: #5f6368;
            pointer-events: none;
            transition: all 0.2s ease;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .download-form-field input {
            width: 100%;
            padding: 32px 16px 12px 16px;
            border: 1px solid #E5E2DC;
            border-radius: 8px;
            font-size: 16px;
            background: #F5F3EF;
            color: #1A1A1A;
            outline: none;
            transition: all 0.2s ease;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .download-form-field input:focus {
            border-color: #017AFF;
            background: #fff;
        }
        .download-form-field input:focus + label,
        .download-form-field input:not(:placeholder-shown) + label {
            top: 8px;
            font-size: 11px;
            color: #017AFF;
        }
        .download-form-field .optional-tag {
            color: #8B4513;
            font-size: 12px;
            margin-left: 4px;
        }
        .download-form-field input::placeholder {
            color: transparent;
        }
        .download-form-field .placeholder-text {
            position: absolute;
            top: 38px;
            left: 16px;
            font-size: 14px;
            color: #999;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        .download-form-field input:focus ~ .placeholder-text,
        .download-form-field input:not(:placeholder-shown) ~ .placeholder-text {
            opacity: 0;
        }
        .download-form-field input:placeholder-shown:not(:focus) ~ .placeholder-text {
            opacity: 1;
        }
        .download-form-consent {
            font-size: 13px;
            color: #5f6368;
            line-height: 1.5;
            margin: 20px 0;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .download-form-consent a {
            color: #8B4513;
            text-decoration: none;
        }
        .download-form-consent a:hover {
            text-decoration: underline;
        }
        .download-form-submit {
            background: #1A1A1A;
            color: #fff;
            border: none;
            padding: 10px 22px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-family: 'Lexend', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .download-form-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-top: 12px;
            font-size: 12px;
            color: #5f6368;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .download-consent {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .download-consent input {
            margin: 0;
        }
        .download-form-submit:hover {
            background: #333;
            transform: translateY(-1px);
        }
        .download-form-submit:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .download-form-error {
            color: #dc3545;
            font-size: 13px;
            margin-top: 4px;
            display: none;
        }
        .download-form-field.error input {
            border-color: #dc3545;
        }
        .download-form-field.error .download-form-error {
            display: block;
        }
        @media (max-width: 480px) {
            .download-modal {
                padding: 24px;
                margin: 16px;
            }
            .download-modal h2 {
                font-size: 20px;
            }
            .download-form-row {
                flex-direction: column;
                gap: 12px;
            }
        }
    </style>
</head>
<body class="iframe-mode loading">
    <div id="flipbook-container">
        <div class="flipbook" id="flipbook"></div>

        <!-- Navigation Arrows -->
        <div class="nav-arrow prev" id="prevBtn" style="display: none;">
            <svg viewBox="0 0 24 24">
                <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
            </svg>
        </div>
        <div class="nav-arrow next" id="nextBtn" style="display: none;">
            <svg viewBox="0 0 24 24">
                <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
            </svg>
        </div>

        <div id="globalLoading" class="page-loading" style="display: flex;">
            <div class="spinner"></div>
            <div class="text">Loading PDF...</div>
        </div>
    </div>

    <!-- Controls Bar -->
    <div id="controls">
        <div class="progress-container">
            <span class="page-info" id="pageInfo">1 / 1</span>
            <div class="progress-bar" id="progressBar">
                <div class="progress-fill" id="progressFill" style="width: 0%">
                    <div class="progress-thumb" id="progressThumb"></div>
                </div>
            </div>
        </div>

        <button class="control-btn" id="downloadBtn">
            <svg viewBox="0 0 24 24">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
            </svg>
            <span id="downloadButtonText">Download</span>
        </button>

        <button class="control-btn" id="fullscreenBtn">
            <svg viewBox="0 0 24 24" id="fullscreenIcon">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
            <span id="fullscreenText">Fullscreen</span>
        </button>
    </div>

    <div id="downloadToast" class="toast-notification">
        <svg viewBox="0 0 24 24">
            <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
        </svg>
        <span>Download started! It will continue in the background.</span>
    </div>

    <div id="downloadModalOverlay" class="download-modal-overlay">
        <div class="download-modal">
            <button class="download-modal-close" id="downloadModalClose">&times;</button>
            <h2>Download a PDF version.</h2>
            <form id="downloadForm">
                <div class="download-form-row">
                    <div class="download-form-field">
                        <input type="text" id="firstName" name="firstName" placeholder=" " required>
                        <label for="firstName">First/Given name</label>
                        <div class="download-form-error">Please enter your first name</div>
                    </div>
                    <div class="download-form-field">
                        <input type="text" id="lastName" name="lastName" placeholder=" ">
                        <label for="lastName">Last/Family name <span class="optional-tag">(optional)</span></label>
                    </div>
                </div>
                <div class="download-form-row">
                    <div class="download-form-field full-width">
                        <input type="email" id="workEmail" name="workEmail" placeholder=" " required>
                        <label for="workEmail">Email</label>
                        <span class="placeholder-text">name@example.com</span>
                        <div class="download-form-error">Please enter a valid email address</div>
                    </div>
                </div>
                <div class="download-form-row">
                    <div class="download-form-field">
                        <input type="text" id="companyName" name="companyName" placeholder=" ">
                        <label for="companyName">Company Name <span class="optional-tag">(optional)</span></label>
                    </div>
                    <div class="download-form-field">
                        <input type="text" id="mobileNumber" name="mobileNumber" placeholder=" ">
                        <label for="mobileNumber">Mobile Number <span class="optional-tag">(optional)</span></label>
                    </div>
                </div>
                <div class="download-form-footer">
                    <span>By downloading, you agree to our <a href="/privacy-policy" target="_blank">Privacy Policy</a>.</span>
                    <button type="submit" class="download-form-submit" id="downloadFormSubmit">Accept and download</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Global variables
        let pdfDoc = null;
        let totalPages = 0;
        let currentPage = 1; // 1-based
        let viewport = null; // Base (scale: 1) viewport for sizing/aspect
        let pagesCache = {}; // {pageNum: { baseViewport, links, lowCanvas, highCanvas }}
        let isFullscreen = false;
        let isDragging = false;
        let pageFlip = null;
        let hasBlankStart = !(window.innerWidth <= 768);

        // Optional: CDN resources for fonts/cmaps if needed by some PDFs
        const PDFJS_VERSION = '3.11.174';
        const CMAP_URL = `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/cmaps/`;
        const STANDARD_FONT_DATA_URL = `https://unpkg.com/pdfjs-dist@${PDFJS_VERSION}/standard_fonts/`;

        // PDF.js configuration
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        // Get PDF URL from query params, data attribute, or default
        const urlParams = new URLSearchParams(window.location.search);
        let pdfUrl = urlParams.get('pdf');
        if (!pdfUrl && typeof INJECTED_PDF_URL !== 'undefined') {
            pdfUrl = INJECTED_PDF_URL;
        }
        if (!pdfUrl) {
            pdfUrl = "https://iwyjssxhrcucnrkzkvmt.supabase.co/storage/v1/object/public/magazine-pdfs/CXO%20TechBOT%20October%202024-1-25.pdf";
        }
        const qualityParam = (urlParams.get('quality') || '').toLowerCase();
        const QUALITY_FACTOR = qualityParam === 'ultra' ? 2.0 : qualityParam === 'high' ? 1.5 : qualityParam === 'med' ? 1.2 : 1.0;

        // Progressive quality: quick low-res for instant paint, then upgrade to high-res
        function getQuickScale() {
            return Math.max(window.devicePixelRatio, 1) * 0.9; // fast
        }
        function getHighScale() {
            return (isFullscreen ? 2.0 : 1.8) * window.devicePixelRatio; // detailed
        }

        // Calculate page dimensions (per single page) based on container and PDF aspect
        function calculatePageDimensions() {
            const container = document.getElementById('flipbook-container');
            const containerWidth = container.clientWidth;
            const containerHeight = container.clientHeight;

            if (!viewport) return { width: 300, height: 400 };

            const pageAspectRatio = viewport.width / viewport.height;
            const padding = isFullscreen ? 40 : 20;
            const controlsHeight = 65; // Height of controls bar

            const availableWidth = containerWidth - (padding * 2);
            const availableHeight = containerHeight - controlsHeight - (padding * 2);

            // Mobile: show one page at a time; Desktop: keep spread (two pages)
            const singlePageMode = window.innerWidth <= 768 || containerWidth <= 768;
            let pageWidth = (availableWidth * 0.98) / (singlePageMode ? 1 : 2);
            let pageHeight = pageWidth / pageAspectRatio;
            if (pageHeight > availableHeight * 0.95) {
                pageHeight = availableHeight * 0.95;
                pageWidth = pageHeight * pageAspectRatio;
            }

            return {
                width: Math.floor(pageWidth),
                height: Math.floor(pageHeight)
            };
        }

        // Render a page at a given quality ('low' | 'high'), caching canvases per page
        async function renderPage(pageNum, quality = 'low') {
            if (!pdfDoc) return null;

            const cache = pagesCache[pageNum];
            if (cache && ((quality === 'low' && cache.lowCanvas) || (quality === 'high' && cache.highCanvas))) {
                return cache;
            }

            try {
                const page = await pdfDoc.getPage(pageNum);

                // Prepare baseViewport and link annotations once
                let baseViewport, links;
                if (!cache) {
                    baseViewport = page.getViewport({ scale: 1 });
                    const annotations = await page.getAnnotations();
                    links = annotations
                        .filter(ann => ann.subtype === 'Link' && ann.url && ann.rect)
                        .map(ann => {
                            try {
                                const [x1, y1, x2, y2] = baseViewport.convertToViewportRectangle(ann.rect);
                                const left = Math.min(x1, x2);
                                const top = Math.min(y1, y2);
                                const width = Math.abs(x2 - x1);
                                const height = Math.abs(y2 - y1);
                                return { url: ann.url, rect: [left, top, width, height] };
                            } catch {
                                return null;
                            }
                        })
                        .filter(Boolean);
                } else {
                    baseViewport = cache.baseViewport;
                    links = cache.links;
                }

                // Choose render scale based on the actual target canvas size for crisp text
                let desiredScale;
                const pageCanvasEl = document.querySelector(`.page[data-page="${pageNum}"] canvas`);
                if (pageCanvasEl && baseViewport) {
                    const targetPxW = pageCanvasEl.width || Math.floor(pageCanvasEl.clientWidth * window.devicePixelRatio);
                    const targetPxH = pageCanvasEl.height || Math.floor(pageCanvasEl.clientHeight * window.devicePixelRatio);
                    const scaleW = targetPxW / baseViewport.width;
                    const scaleH = targetPxH / baseViewport.height;
                    const displayScale = Math.min(scaleW, scaleH);
                    // Match canvas pixel ratio for 1:1 mapping to maximize clarity
                    const oversample = 1.0;
                    desiredScale = Math.max(1, displayScale * oversample);
                } else {
                    // Fallback if page canvas is not in DOM yet
                    desiredScale = quality === 'low' ? getQuickScale() : getHighScale();
                }
                const renderViewport = page.getViewport({ scale: desiredScale });

                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d', { alpha: false });
                canvas.height = renderViewport.height;
                canvas.width = renderViewport.width;

                await page.render({
                    canvasContext: context,
                    viewport: renderViewport
                }).promise;

                pagesCache[pageNum] = {
                    ...(cache || {}),
                    baseViewport,
                    links,
                    lowCanvas: quality === 'low' ? canvas : (cache ? cache.lowCanvas : null),
                    highCanvas: quality === 'high' ? canvas : (cache ? cache.highCanvas : null),
                };

                return pagesCache[pageNum];
            } catch (error) {
                console.error(`Error rendering page ${pageNum} (${quality}):`, error);
                return null;
            }
        }

        // Add URL overlay highlights into a .page-content element
        function addUrlOverlays(pageContent, links, baseViewport, dimensions) {
            // Use percentage-based positioning so overlays stay aligned across resize/zoom/fullscreen
            const bw = baseViewport.width || 1;
            const bh = baseViewport.height || 1;

            links.forEach(link => {
                const [left, top, width, height] = link.rect;
                const overlay = document.createElement('div');
                overlay.className = 'url-overlay';
                overlay.style.left = `${(left / bw) * 100}%`;
                overlay.style.top = `${(top / bh) * 100}%`;
                overlay.style.width = `${Math.max(0, (width / bw) * 100)}%`;
                overlay.style.height = `${Math.max(0, (height / bh) * 100)}%`;
                overlay.dataset.url = link.url;
                overlay.title = `Click to open: ${link.url}`;
                overlay.addEventListener('click', (e) => {
                    e.stopPropagation();
                    window.open(link.url, '_blank');
                });
                pageContent.appendChild(overlay);
            });
        }

        // Create a PageFlip-compatible page shell with canvas
        function createFlipPageShell(pageNum, dimensions) {
            const page = document.createElement('div');
            page.className = 'page';
            page.dataset.page = pageNum;
            page.style.width = `${dimensions.width}px`;
            page.style.height = `${dimensions.height}px`;

            const content = document.createElement('div');
            content.className = 'page-content';
            content.style.width = '100%';
            content.style.height = '100%';

            const canvas = document.createElement('canvas');
            // Increase backing resolution for sharper text (super-sampling)
            const mult = (isFullscreen ? 3.0 : 2.0) * QUALITY_FACTOR;
            canvas.width = Math.floor(dimensions.width * window.devicePixelRatio * mult);
            canvas.height = Math.floor(dimensions.height * window.devicePixelRatio * mult);
            canvas.style.width = '100%';
            canvas.style.height = '100%';

            content.appendChild(canvas);
            page.appendChild(content);
            return { page, content, canvas };
        }

        // Create a blank page shell to ensure symmetric animation on first/last flips
        function createBlankPageShell(dimensions) {
            const page = document.createElement('div');
            page.className = 'page';
            page.dataset.blank = 'true';
            page.style.width = `${dimensions.width}px`;
            page.style.height = `${dimensions.height}px`;

            const content = document.createElement('div');
            content.className = 'page-content';
            content.style.width = '100%';
            content.style.height = '100%';

            page.appendChild(content);
            return page;
        }

        // Draw provided source canvas into target canvas (scaled)
        function drawInto(targetCanvas, sourceCanvas) {
            const ctx = targetCanvas.getContext('2d', { alpha: false });
            ctx.imageSmoothingEnabled = true;
            if (ctx.imageSmoothingQuality) ctx.imageSmoothingQuality = 'high';
            ctx.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
            ctx.drawImage(
                sourceCanvas,
                0, 0, sourceCanvas.width, sourceCanvas.height,
                0, 0, targetCanvas.width, targetCanvas.height
            );
        }

        // Upgrade an existing .page canvas to high quality
        async function upgradePageCanvasToHigh(pageNum, dimensions) {
            const data = await renderPage(pageNum, 'high');
            if (!data) return;
            const pageEl = document.querySelector(`.page[data-page="${pageNum}"]`);
            if (!pageEl) return;
            const canvas = pageEl.querySelector('canvas');
            if (!canvas) return;
            drawInto(canvas, data.highCanvas);
        }

        // Rebuild all page canvases at current size/quality (useful after fullscreen/resize)
        function rebuildAllPagesForQuality() {
            const dims = calculatePageDimensions();
            const pages = document.querySelectorAll('#flipbook .page');
            pages.forEach((pageEl) => {
                if (pageEl.dataset.blank === 'true') return;
                const canvas = pageEl.querySelector('canvas');
                if (!canvas) return;
                const dpr = window.devicePixelRatio || 1;
                const mult = (isFullscreen ? 3.0 : 2.0) * QUALITY_FACTOR;
                const targetW = Math.floor(dims.width * dpr * mult);
                const targetH = Math.floor(dims.height * dpr * mult);
                if (canvas.width === targetW && canvas.height === targetH) return;
                canvas.width = targetW;
                canvas.height = targetH;
                const pageNum = parseInt(pageEl.dataset.page, 10);
                if (!isNaN(pageNum)) {
                    upgradePageCanvasToHigh(pageNum, dims);
                }
            });
        }

        // Update controls
        function updateControls() {
            document.getElementById('pageInfo').textContent = `${currentPage} / ${totalPages}`;
            const progress = totalPages > 1 ? ((currentPage - 1) / (totalPages - 1)) * 100 : 0;
            document.getElementById('progressFill').style.width = `${progress}%`;

            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');

            if (currentPage <= 1) {
                prevBtn.classList.add('disabled');
            } else {
                prevBtn.classList.remove('disabled');
            }

            if (currentPage >= totalPages) {
                nextBtn.classList.add('disabled');
            } else {
                nextBtn.classList.remove('disabled');
            }
        }

        // Progress bar drag functionality
        function initProgressBar() {
            const progressBar = document.getElementById('progressBar');
            const progressThumb = document.getElementById('progressThumb');

            function updateProgressFromMouse(e) {
                const rect = progressBar.getBoundingClientRect();
                const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
                const progress = x / rect.width;
                const targetPage = Math.max(1, Math.min(totalPages, Math.round(progress * (totalPages - 1) + 1)));
                if (targetPage !== currentPage) {
                    if (pageFlip) pageFlip.turnToPage(hasBlankStart ? targetPage : targetPage - 1);
                }
            }

            progressThumb.addEventListener('mousedown', (e) => {
                isDragging = true;
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (isDragging) updateProgressFromMouse(e);
            });

            document.addEventListener('mouseup', () => {
                isDragging = false;
            });

            progressBar.addEventListener('click', (e) => {
                if (!isDragging) updateProgressFromMouse(e);
            });
        }

        // Navigation buttons using PageFlip
        document.getElementById('prevBtn').addEventListener('click', () => {
            if (!pageFlip) return;
            if (currentPage <= 1) return;
            pageFlip.flipPrev();
        });

        document.getElementById('nextBtn').addEventListener('click', () => {
            if (!pageFlip) return;
            if (currentPage >= totalPages) return;
            pageFlip.flipNext();
        });

        function showDownloadToast() {
            const toast = document.getElementById('downloadToast');
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        function showDownloadModal() {
            const overlay = document.getElementById('downloadModalOverlay');
            overlay.classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function hideDownloadModal() {
            const overlay = document.getElementById('downloadModalOverlay');
            overlay.classList.remove('show');
            document.body.style.overflow = '';
            const form = document.getElementById('downloadForm');
            form.reset();
            document.querySelectorAll('.download-form-field').forEach(field => {
                field.classList.remove('error');
            });
        }

        function validateEmail(email) {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(email);
        }

        function performDownload() {
            const filename = (pdfUrl.split('/').pop() || 'document.pdf');
            
            showDownloadToast();
            
            try {
                const parentOrigin = (() => {
                    try { return new URL(document.referrer).origin; } catch { return null; }
                })();
                if (parentOrigin) {
                    const proxiedUrl = `${parentOrigin}/download_proxy?pdf=${encodeURIComponent(pdfUrl)}&filename=${encodeURIComponent(filename)}`;
                    const a = document.createElement('a');
                    a.href = proxiedUrl;
                    a.download = filename;
                    a.target = '_blank';
                    a.rel = 'noopener';
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    return;
                }
            } catch (_) {
            }
            if (window.parent && window.parent !== window) {
                window.parent.postMessage({ action: 'download', pdfUrl, filename }, '*');
            } else {
                const a = document.createElement('a');
                a.href = pdfUrl;
                a.download = filename;
                a.target = '_blank';
                a.rel = 'noopener';
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }
        }

        async function submitDownloadForm(firstName, lastName, email, companyName, mobileNumber) {
            try {
                const parentOrigin = (() => {
                    try { return new URL(document.referrer).origin; } catch { return window.location.origin; }
                })();
                
                const response = await fetch(`${parentOrigin}/api/pdf-download-form`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        first_name: firstName,
                        last_name: lastName,
                        email: email,
                        company_name: companyName,
                        mobile_number: mobileNumber,
                        pdf_link: pdfUrl
                    })
                });
                
                return response.ok;
            } catch (error) {
                console.error('Error submitting form:', error);
                return false;
            }
        }

        document.getElementById('downloadBtn').addEventListener('click', () => {
            showDownloadModal();
        });

        document.getElementById('downloadModalClose').addEventListener('click', () => {
            hideDownloadModal();
        });

        document.getElementById('downloadModalOverlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                hideDownloadModal();
            }
        });

        document.getElementById('downloadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const firstName = document.getElementById('firstName').value.trim();
            const lastName = document.getElementById('lastName').value.trim();
            const email = document.getElementById('workEmail').value.trim();
            const companyName = document.getElementById('companyName').value.trim();
            const mobileNumber = document.getElementById('mobileNumber').value.trim();
            
            let hasError = false;
            
            document.querySelectorAll('.download-form-field').forEach(field => {
                field.classList.remove('error');
            });
            
            if (!firstName) {
                document.getElementById('firstName').closest('.download-form-field').classList.add('error');
                hasError = true;
            }
            
            if (!email || !validateEmail(email)) {
                document.getElementById('workEmail').closest('.download-form-field').classList.add('error');
                hasError = true;
            }
            
            if (hasError) return;
            
            const submitBtn = document.getElementById('downloadFormSubmit');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            
            await submitDownloadForm(firstName, lastName, email, companyName, mobileNumber);
            
            hideDownloadModal();
            performDownload();
            
            submitBtn.disabled = false;
            submitBtn.textContent = 'Download now';
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const overlay = document.getElementById('downloadModalOverlay');
                if (overlay.classList.contains('show')) {
                    hideDownloadModal();
                }
            }
        });

        // Fullscreen button
        document.getElementById('fullscreenBtn').addEventListener('click', () => {
            if (!isFullscreen) {
                if (document.documentElement.requestFullscreen) {
                    document.documentElement.requestFullscreen();
                } else if (document.documentElement.webkitRequestFullscreen) {
                    document.documentElement.webkitRequestFullscreen();
                } else if (document.documentElement.msRequestFullscreen) {
                    document.documentElement.msRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            }
        });

        // Fullscreen change handler (keeps auto-resize)
        function handleFullscreenChange() {
            isFullscreen = document.fullscreenElement ||
                           document.webkitFullscreenElement ||
                           document.msFullscreenElement;

            const fullscreenIcon = document.getElementById('fullscreenIcon');
            const fullscreenText = document.getElementById('fullscreenText');

            if (isFullscreen) {
                document.body.classList.remove('iframe-mode');
                document.body.classList.add('fullscreen-mode');
                fullscreenIcon.innerHTML = '<path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>';
                fullscreenText.textContent = 'Exit Fullscreen';
            } else {
                document.body.classList.add('iframe-mode');
                document.body.classList.remove('fullscreen-mode');
                fullscreenIcon.innerHTML = '<path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>';
                fullscreenText.textContent = 'Fullscreen';
            }

            // Trigger PageFlip to recalc and fit container automatically
            if (pageFlip) {
                // small defer to allow layout to settle
                setTimeout(() => {
                    pageFlip.update();
                    // then rebuild canvases at higher backing resolution for crispness
                    setTimeout(rebuildAllPagesForQuality, 100);
                }, 50);
            }
        }

        document.addEventListener('fullscreenchange', handleFullscreenChange);
        document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
        document.addEventListener('msfullscreenchange', handleFullscreenChange);

        // Listen for messages from parent (iframe control)
        window.addEventListener('message', (event) => {
            const msg = event.data || {};
            const msgType = msg.type || msg.action;

            if (msgType === 'flipToPage') {
                if (pageFlip) {
                    const tp = Math.max(1, Math.min(totalPages, msg.page || 1));
                    pageFlip.turnToPage(hasBlankStart ? tp : tp - 1);
                }
            } else if (msgType === 'nextPage') {
                if (pageFlip && currentPage < totalPages) pageFlip.flipNext();
            } else if (msgType === 'prevPage') {
                if (pageFlip && currentPage > 1) pageFlip.flipPrev();
            } else if (msgType === 'toggleFullscreen') {
                document.getElementById('fullscreenBtn').click();
            } else if (msgType === 'download') {
                // Trigger the download flow (which posts back to parent for actual download)
                document.getElementById('downloadBtn').click();
            }
        });

        // Initialize PDF and PageFlip
        function initPDF() {
            const flipbook = document.getElementById('flipbook');
            document.getElementById('prevBtn').style.display = 'flex';
            document.getElementById('nextBtn').style.display = 'flex';
            initProgressBar();

            // Start loading PDF (fast-first-page)
            const loadingTask = pdfjsLib.getDocument({
                url: pdfUrl,
                disableAutoFetch: true,
                disableStream: false,
                disableRange: false,
                cMapUrl: CMAP_URL,
                cMapPacked: true,
                standardFontDataUrl: STANDARD_FONT_DATA_URL,
                withCredentials: false
            });

            loadingTask.onProgress = function (progress) {
                const loader = document.getElementById('globalLoading');
                if (!loader) return;
                if (progress.total > 0) {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    const textEl = loader.querySelector('.text');
                    if (textEl) textEl.textContent = `Loading PDF: ${percent}%`;
                }
            };

            loadingTask.promise.then(async (doc) => {
                pdfDoc = doc;
                totalPages = pdfDoc.numPages;

                // Establish base viewport quickly from page 1 only (scale: 1)
                const firstPage = await pdfDoc.getPage(1);
                viewport = firstPage.getViewport({ scale: 1 });

                document.getElementById('pageInfo').textContent = `1 / ${totalPages}`;
                const dims = calculatePageDimensions();

                // Build DOM shells for all pages
                flipbook.innerHTML = '';
                const pageEls = [];
                if (hasBlankStart) {
                    const blank = createBlankPageShell(dims);
                    flipbook.appendChild(blank);
                }
                for (let i = 1; i <= totalPages; i++) {
                    const { page, content, canvas } = createFlipPageShell(i, dims);
                    flipbook.appendChild(page);
                    pageEls.push(page);

                    // Render first pages at high quality for readability; others low then upgrade
                    setTimeout(async () => {
                        if (i <= 2) {
                            const dataHigh = await renderPage(i, 'high');
                            if (dataHigh) {
                                drawInto(canvas, dataHigh.highCanvas);
                                if (dataHigh.links && dataHigh.links.length > 0) {
                                    addUrlOverlays(content, dataHigh.links, dataHigh.baseViewport, dims);
                                }
                            }
                        } else {
                            const dataLow = await renderPage(i, 'low');
                            if (dataLow) {
                                drawInto(canvas, dataLow.lowCanvas);
                                if (dataLow.links && dataLow.links.length > 0) {
                                    addUrlOverlays(content, dataLow.links, dataLow.baseViewport, dims);
                                }
                                // Upgrade to high in background
                                upgradePageCanvasToHigh(i, dims).catch(() => {});
                            }
                        }
                    }, i * 30);
                }

                // If we have a leading blank and an even number of PDF pages,
                // append a trailing blank to keep the last spread symmetrical (all soft pages).
                if (hasBlankStart && (totalPages % 2 === 0)) {
                    const trailingBlank = createBlankPageShell(dims);
                    flipbook.appendChild(trailingBlank);
                }

                // Init PageFlip (cover + soft pages, first page soft)
                pageFlip = new St.PageFlip(flipbook, {
                    width: Math.max(320, dims.width),
                    height: Math.max(400, dims.height),
                    size: (window.innerWidth <= 768 || document.getElementById('flipbook-container').clientWidth <= 768) ? 'fixed' : 'stretch',       // force single-page on mobile; stretch on larger screens
                    minWidth: 300,
                    maxWidth: 4000,
                    minHeight: 400,
                    maxHeight: 6000,
                    showCover: false,      // treat all pages the same; no special cover
                    usePortrait: true,
                    autoSize: true,
                    drawShadow: true,
                    flippingTime: 700,
                    maxShadowOpacity: 0.5,
                    mobileScrollSupport: true
                });

                pageFlip.loadFromHTML(document.querySelectorAll('#flipbook .page'));
                if (hasBlankStart) pageFlip.turnToPage(1);

                // Events
                pageFlip.on('flip', (e) => {
                    const idx = (e.data || 0);
                    currentPage = hasBlankStart ? Math.min(totalPages, Math.max(1, idx)) : Math.min(totalPages, idx + 1);
                    updateControls();
                    if (window.parent !== window) {
                        window.parent.postMessage({
                            type: 'pageChange',
                            currentPage: currentPage,
                            totalPages: totalPages
                        }, '*');
                    }
                    // Ensure current spread renders in high resolution immediately
                    const dims = calculatePageDimensions();
                    const leftPage = currentPage % 2 === 0 ? currentPage : Math.max(1, currentPage - 1);
                    const rightPage = Math.min(totalPages, leftPage + 1);
                    upgradePageCanvasToHigh(leftPage, dims);
                    if (rightPage !== leftPage) upgradePageCanvasToHigh(rightPage, dims);
                });

                // Set initial state
                currentPage = 1;
                updateControls();

                // Remove loading overlay
                const loader = document.getElementById('globalLoading');
                if (loader) loader.style.display = 'none';
                document.body.classList.remove('loading');

                // Preload additional pages (render low if missing)
                preloadPages(2, 8);

                if (window.parent !== window) {
                    window.parent.postMessage({
                        type: 'flipbookReady',
                        totalPages: totalPages
                    }, '*');
                }
            }).catch(error => {
                console.error('Error loading PDF:', error);
                document.getElementById('globalLoading').innerHTML = `
                    <div style="color: white; text-align: center; padding: 20px;">
                        <h3>Error loading PDF</h3>
                        <p>${error.message || 'Please try refreshing the page'}</p>
                    </div>
                `;
            });
        }

        // Pre-load pages in the background (low-quality only to avoid blocking)
        function preloadPages(startPage, count = 4) {
            const pagesToLoad = [];
            for (let i = startPage; i <= Math.min(startPage + count - 1, totalPages); i++) {
                if (!pagesCache[i] || !pagesCache[i].lowCanvas) {
                    pagesToLoad.push(i);
                }
            }
            pagesToLoad.forEach(pageNum => {
                setTimeout(() => {
                    renderPage(pageNum, 'low').catch(() => {});
                }, (pageNum - startPage) * 100);
            });
        }

        // Handle window resize (PageFlip autoresizes; call update to recalc)
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                if (pageFlip) {
                    pageFlip.update();
                    rebuildAllPagesForQuality();
                }
            }, 150);
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!pageFlip) return;
            if (e.key === 'ArrowLeft') {
                if (hasBlankStart && currentPage <= 1) return; // prevent flipping to leading blank
                pageFlip.flipPrev();
            } else if (e.key === 'ArrowRight') {
                pageFlip.flipNext();
            } else if (e.key === 'f' || e.key === 'F') {
                document.getElementById('fullscreenBtn').click();
            }
        });

        // Initialize immediately when script loads
        initPDF();
    </script>
</body>
</html>

"""

def get_raw_html(pdf_url):
    """
    Generate clean iframe HTML for PDF viewer without ad banners.
    
    Args:
        pdf_url: URL or filename of the PDF to display
        
    Returns:
        Complete iframe HTML with embedded PDF viewer and download handler
    """
    if not pdf_url:
        raise ValueError("PDF URL must be provided")
    
    pdf_injection = f"""
    <script>
        const INJECTED_PDF_URL = '{pdf_url}';
    </script>
    """
    
    raw_html = MAGAZINE_IFRAME_CONTENT.replace('<script>', pdf_injection + '<script>', 1)
    escaped_html = raw_html.replace('&', '&amp;').replace("'", '&#39;').replace('"', '&quot;')

    iframe = f"""<iframe
                id="my-flipbook-container"
                class="w-full max-w-[52rem]"
                title="PDF Flipbook Viewer - Interactive document viewer"
                allow="clipboard-write"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
                allowfullscreen="true"
                style="border:none;overflow:hidden;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);border:1px solid #e5e7eb;background-color:#000;height:100%;width:100%;"
                srcdoc='{escaped_html}'
              ></iframe>""" + """
              <script>
                (function () {
                  var iframeEl = document.getElementById('my-flipbook-container');
                  function triggerDownload(url, filename) {
                    try {
                      var safeName = filename || (url ? url.split('/').pop() : 'document.pdf') || 'document.pdf';
                      var proxiedUrl = window.location.origin + "/download_proxy?pdf=" + encodeURIComponent(url) + "&filename=" + encodeURIComponent(safeName);
                      var a = document.createElement('a');
                      a.href = proxiedUrl;
                      a.download = safeName;
                      a.style.display = 'none';
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                    } catch (err) {
                      console.error('Parent download error:', err);
                    }
                  }
                  window.addEventListener('message', function (event) {
                    try {
                      if (!iframeEl || event.source !== iframeEl.contentWindow) return;
                      var data = event.data || {};
                      var type = data.type || data.action;
                      if (type === 'download' || type === 'downloadResponse') {
                        triggerDownload(data.pdfUrl, data.filename);
                      }
                    } catch (e) {
                      console.error('Parent message handler error:', e);
                    }
                  });
                  document.addEventListener('keydown', function (e) {
                    if (!iframeEl || !iframeEl.contentWindow) return;
                    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
                    if (e.key === 'ArrowLeft') {
                      e.preventDefault();
                      iframeEl.contentWindow.postMessage({ type: 'prevPage' }, '*');
                    } else if (e.key === 'ArrowRight') {
                      e.preventDefault();
                      iframeEl.contentWindow.postMessage({ type: 'nextPage' }, '*');
                    } else if (e.key === 'f' || e.key === 'F') {
                      e.preventDefault();
                      iframeEl.contentWindow.postMessage({ type: 'toggleFullscreen' }, '*');
                    }
                  });
                })();
              </script>
    """
    return iframe



def sanitize_html_preserve_formatting(html_content: str) -> str:
    """
    Sanitize HTML content while preserving text formatting (bold, italic, underline)
    Converts inline styled spans to semantic HTML tags
    """
    if not html_content:
        return ""
    
    content = html_content
    
    content = re.sub(r'<!--StartFragment-->', '', content)
    content = re.sub(r'<!--EndFragment-->', '', content)
    content = re.sub(r'<meta[^>]*?>', '', content)
    content = re.sub(r'<br\s+class=[^>]*?>', '<br>', content)
    content = re.sub(r'<div[^>]*?></div>', '', content)
    content = re.sub(r'<div[^>]*?>', '', content)
    content = re.sub(r'</div>', '', content)
    
    content = re.sub(r'<b[^>]*?style="font-weight:normal;"[^>]*?>', '', content)
    content = re.sub(r'<b[^>]*?>', '', content)
    content = re.sub(r'</b>', '', content)
    
    def convert_styled_span(match):
        style = match.group(1) if match.lastindex >= 1 else ''
        inner_content = match.group(2) if match.lastindex >= 2 else ''
        
        if not inner_content:
            return ''
        
        tags_open = []
        tags_close = []
        
        if 'font-weight: 700' in style or 'font-weight:700' in style:
            tags_open.append('<strong>')
            tags_close.insert(0, '</strong>')
        
        if 'font-style: italic' in style or 'font-style:italic' in style:
            tags_open.append('<em>')
            tags_close.insert(0, '</em>')
        
        if 'text-decoration: underline' in style or 'text-decoration:underline' in style:
            tags_open.append('<u>')
            tags_close.insert(0, '</u>')
        
        if tags_open:
            return ''.join(tags_open) + inner_content + ''.join(tags_close)
        return inner_content
    
    content = re.sub(
        r'<span[^>]*?style="([^"]*?)"[^>]*?>(.*?)</span>',
        convert_styled_span,
        content,
        flags=re.DOTALL
    )
    
    content = re.sub(r'<span[^>]*?>(.*?)</span>', r'\1', content, flags=re.DOTALL)
    
    content = re.sub(r'&nbsp;', ' ', content)
    content = re.sub(r'&amp;', '&', content)
    content = re.sub(r'&lt;', '<', content)
    content = re.sub(r'&gt;', '>', content)
    content = re.sub(r'&quot;', '"', content)
    
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    return content


def strip_html_tags(html_content: str) -> str:
    """
    Remove HTML tags from content and return plain text
    DEPRECATED: Use sanitize_html_preserve_formatting() instead
    """
    if not html_content:
        return ""
    
    clean_text = re.sub(r'<[^>]+>', '', html_content)
    clean_text = re.sub(r'&nbsp;', ' ', clean_text)
    clean_text = re.sub(r'&amp;', '&', clean_text)
    clean_text = re.sub(r'&lt;', '<', clean_text)
    clean_text = re.sub(r'&gt;', '>', clean_text)
    clean_text = re.sub(r'&quot;', '"', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return clean_text.strip()


def parse_blog_json(blog_json_str: str) -> Dict[str, Any]:
    """
    Parse the blog JSON string into a dictionary
    """
    try:
        return json.loads(blog_json_str)
    except (json.JSONDecodeError, TypeError):
        return {}


def format_date(date_str: str) -> tuple[str, str]:
    """
    Format date string to human-readable format and ISO format
    Returns tuple of (formatted_date, iso_date)
    """
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        formatted = date_obj.strftime("%B %d, %Y")
        iso = date_obj.strftime("%Y-%m-%d")
        return formatted, iso
    except:
        return "Unknown Date", "2025-01-01"


def generate_head_section(blog_data: Dict[str, Any], case_study_date: str) -> str:
    """
    Generate the HTML head section with meta tags, SEO, and structured data
    """
    title = blog_data.get('seoTitle', blog_data.get('blogTitle', 'Case Study'))
    description = blog_data.get('seoMetaDescription', blog_data.get('seoTitle', ''))
    image_url = blog_data.get('mainImageUrl', 'https://picsum.photos/1920/1080/?random=123')
    formatted_date, iso_date = format_date(case_study_date)
    
    return f"""<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />

    <meta name="description" content="{description}" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{description}" />
    <meta property="og:type" content="article" />
    <meta property="og:image" content="{image_url}" />
    <meta property="twitter:card" content="summary_large_image" />
    <meta property="twitter:title" content="{title}" />
    <meta property="twitter:description" content="{description}" />
    <meta property="twitter:image" content="{image_url}" />

    <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link rel="preconnect" href="https://unpkg.com" crossorigin />
    <link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin />
    <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
    <link
        href="https://fonts.googleapis.com/css2?family=Lexend:wght@100..900&family=Playfair+Display:wght@400;600;700;800;900&family=Source+Sans+Pro:wght@300;400;600;700&display=swap"
        rel="stylesheet" />
    <link rel="stylesheet" href="/css/case_study.css" />
    <script src="https://unpkg.com/lucide@latest" defer></script>

    <script type="application/ld+json">
        {{
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "{title}",
            "datePublished": "{iso_date}",
            "description": "{description}",
            "image": ["{image_url}"],
            "articleSection": "CASE STUDY"
        }}
  </script>
</head>

<body>
    <a href="#main" class="visually-hidden">Skip to content</a>"""


def generate_header_section() -> str:
    """
    Generate the header section with navigation
    """
    return """
    <header class="header">
        <div class="logo">
            <a href="/"><img src="/images/logo_header.png" alt="Suflex Media Logo" width="120" height="56"></a>
        </div>
        <nav class="nav-links">
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <div class="dropdown">
                <span class="dropdown-toggle">Services <i data-lucide="chevron-down" class="dropdown-arrow"></i></span>
                <div class="dropdown-menu">
                    <a href="/ghostwriting">Book Writing</a>
                    <a href="/linkedin-branding">LinkedIn Branding</a>
                    <a href="/content-writing">Content Writing</a>
                    <a href="/performance-marketing">Performance Marketing</a>
                    <a href="/website-development">Website Development</a>
                    <a href="/seo">Search Engine Optimisation</a>
                </div>
            </div>
            <a href="/case-studies" class="active">Case Studies</a>
            <a href="/blogs">Blog</a>
            <a href="/contact" class="contact-us">
                <img src="/icons/phone-icon.png" alt="Phone icon" class="icon" width="24" height="24">
                <span>Contact Us</span>
            </a>
        </nav>
        <a href="/contact" class="contact-us">
            <img src="/icons/phone-icon.png" alt="Phone icon" class="icon" width="24" height="24">
            <span>Contact Us</span>
        </a>
        <div class="hamburger">
            <span></span>
            <span></span>
            <span></span>
        </div>
    </header>

    <main id="main" class="wrap" role="main" aria-labelledby="title">"""


def generate_article_header(blog_data: Dict[str, Any], case_study_date: str, category: str = None) -> str:
    """
    Generate the article header section with breadcrumbs, title, and date
    """
    title = blog_data.get('blogTitle', 'Case Study')
    formatted_date, iso_date = format_date(case_study_date)
    
    breadcrumb_html = "Case Study"
    if category:
        breadcrumb_html = f'Case Study <svg class="breadcrumb-arrow" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg> {category} <svg class="breadcrumb-arrow" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg> '
    
    return f"""
        <header class="article-header">
            <span class="kicker" aria-label="Content type">
                {breadcrumb_html}
            </span>
            <h1 id="title" class="title">{title}</h1>
            <div class="meta">
                <span>Published: <time datetime="{iso_date}">{formatted_date}</time></span>
            </div>
        </header>"""


def generate_summary_section(previewData: Dict[str, Any]) -> str:
    """
    Generate the summary/lead section
    """
    summary = previewData.get('summary', '')
    clean_summary = sanitize_html_preserve_formatting(summary)
    
    if not clean_summary:
        return ""
    
    return f"""
        <section aria-label="Summary">
            <div class="lead">
                {clean_summary}
            </div>
        </section>"""


def generate_vision_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the vision section
    """
    structured_content = blog_data.get('structuredContent', {})
    vision_html = structured_content.get('theVision', '')
    vision_text = sanitize_html_preserve_formatting(vision_html)
    
    if not vision_text:
        return ""
    
    return f"""
        <section class="section" aria-label="Vision">
            <h2>The Vision</h2>
            <div class="prose">
                {vision_text}
            </div>
        </section>"""


def generate_process_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the process section with intro, steps, and conclusion
    """
    structured_content = blog_data.get('structuredContent', {})
    our_process = structured_content.get('ourProcess', {})
    
    if not our_process:
        return ""
    
    intro_html = our_process.get('intro', '')
    intro_text = sanitize_html_preserve_formatting(intro_html)
    
    steps = our_process.get('steps', [])
    steps_html = ""
    for step in steps:
        step_text = sanitize_html_preserve_formatting(step)
        if step_text:
            steps_html += f"                    <li>{step_text}</li>\n"
    
    conclusion_html = our_process.get('conclusion', '')
    conclusion_text = sanitize_html_preserve_formatting(conclusion_html)
    
    if not intro_text and not steps_html and not conclusion_text:
        return ""
    
    section = f"""
        <section class="section" aria-label="Our process">
            <h2>Our Process</h2>
            <div class="process">"""
    
    if intro_text:
        section += f"""
                {intro_text}"""
    
    if steps_html:
        section += f"""
                <ol class="steps">
{steps_html}                </ol>"""
    
    if conclusion_text:
        section += f"""
                {conclusion_text}"""
    
    section += """
            </div>
        </section>"""
    
    return section


def generate_story_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the story section with dynamic h3 subsections
    """
    structured_content = blog_data.get('structuredContent', {})
    the_story = structured_content.get('theStory', [])
    
    if not the_story:
        return ""
    
    section = f"""
        <section class="section" aria-label="The story we told">
            <h2>The Story We Told</h2>
            <div class="prose">"""
    
    for item in the_story:
        if item.get('type') == 'h3':
            title = item.get('title', '')
            content_html = item.get('content', '')
            content_text = sanitize_html_preserve_formatting(content_html)
            
            if title and content_text:
                section += f"""
                <h3>{title}</h3>
                {content_text}
"""
    
    section += """            </div>
        </section>"""
    
    return section


def generate_result_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the result section
    """
    structured_content = blog_data.get('structuredContent', {})
    result_html = structured_content.get('theResult', '')
    result_text = sanitize_html_preserve_formatting(result_html)
    
    if not result_text:
        return ""
    
    section = f"""
        <section class="section" aria-label="Result">
            <h2>The Result</h2>
            <div class="result">
                {result_text}
            </div>
        </section>"""
    
    return section


def generate_impact_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the impact section with list items
    """
    structured_content = blog_data.get('structuredContent', {})
    the_impact = structured_content.get('theImpact', [])
    
    if not the_impact:
        return ""
    
    section = f"""
        <section class="section" aria-label="Impact">
            <h2>The Impact</h2>
            <ul class="impact-list">"""
    
    for impact_item_html in the_impact:
        impact_text = sanitize_html_preserve_formatting(impact_item_html)
        if impact_text:
            section += f"""
                <li class="impact-item">
                    <span>{impact_text}</span>
                </li>"""
    
    section += """
            </ul>
        </section>"""
    
    return section


def generate_pdf_viewer_section(pdf_url: Optional[str]) -> str:
    """
    Generate the PDF viewer iframe section
    """
    if not pdf_url:
        return ""
    
    iframe_html = get_raw_html(pdf_url)
    
    return f"""
        <section class="section pdf-viewer-section" aria-label="PDF Viewer">
            <div class="pdf-container" style="width: 100%; height: 550px; display: flex; justify-content: center; align-items: center; background: #1a1a1a; border-radius: 8px; overflow: hidden;">
                {iframe_html}
            </div>
        </section>"""


def generate_footer_section(blog_data: Dict[str, Any]) -> str:
    """
    Generate the footer section
    """
    return """
    </main>

    <footer class="footer">
        <div class="footer-content">
            <div class="footer-section cta">
                <h2>Ready to grow your<br>business?</h2>
                <a href="/contact" class="button">Book a free strategy call</a>
            </div>
            <div class="footer-section">
                <h3>Quick Links</h3>
                <a href="/">Home</a>
                <a href="/about">About Us</a>
                <a href="/services">Services</a>
                <a href="/blogs">Blog</a>
            </div>
            <div class="footer-section">
                <h3>Services</h3>
                <a href="/ghostwriting">Book Writing</a>
                <a href="/linkedin-branding">LinkedIn Branding</a>
                <a href="/content-writing">Content Writing</a>
                <a href="/performance-marketing">Performance Marketing</a>
                <a href="/website-development">Website Development</a>
            </div>
            <div class="footer-section social-section">
                <h3>Social Links</h3>
                <div class="social-links">
                    <a href="#"><img src="/icons/instagram.png" alt="Instagram" width="32" height="32"></a>
                    <a href="#"><img src="/icons/linkedin.png" alt="LinkedIn" width="32" height="32"></a>
                    <a href="#"><img src="/icons/x.png" alt="X" width="32" height="32"></a>
                </div>
            </div>
            <div class="footer-section contact-section">
                <h3>Contact Us</h3>
                <a href="mailto:hello@suflexmedia.com">hello@suflexmedia.com</a>
            </div>
        </div>
        <div class="footer-bottom">
            <div class="footer-logo">
                <img src="/images/logo_header.png" alt="Suflex Media Logo" width="150" height="70">
            </div>
            <div class="copyright">
                <p>Copyright © 2025 SuflexMedia | All Rights Reserved</p>
            </div>
        </div>
    </footer>

    <script>
        const originalTitle = document.title;
        const awayTitle = "Missing you already!";
        const originalFavicon = "/images/logo_header.png";
        
        function createEmojiFavicon(emoji) {
            const canvas = document.createElement('canvas');
            canvas.width = 32;
            canvas.height = 32;
            const ctx = canvas.getContext('2d');
            ctx.font = '28px serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(emoji, 16, 18);
            return canvas.toDataURL('image/png');
        }
        
        const awayFavicon = createEmojiFavicon('😢');
        
        function setFavicon(href) {
            let link = document.querySelector("link[rel*='icon']");
            if (!link) {
                link = document.createElement('link');
                link.rel = 'icon';
                document.head.appendChild(link);
            }
            link.href = href;
        }

        document.addEventListener("visibilitychange", function() {
            if (document.hidden) {
                document.title = awayTitle;
                setFavicon(awayFavicon);
            } else {
                document.title = originalTitle;
                setFavicon(originalFavicon);
            }
        });
        
        lucide.createIcons();
    </script>
    <script src="/js/case_study.js"></script>
</body>

</html>"""


def assemble_case_study_html(case_study_data: Dict[str, Any]) -> str:
    """
    Main orchestrator function that assembles all HTML sections into complete page
    """
    blog_json_str = case_study_data.get('blog', '{}')
    blog_data = parse_blog_json(blog_json_str)
    case_study_date = case_study_data.get('date', '')
    pdf_url = case_study_data.get('pdf_url')
    category = case_study_data.get('category', '')
    
    preview_json_str = case_study_data.get('preview', '{}')
    preview_data = parse_blog_json(preview_json_str)
    
    html_parts = [
        generate_head_section(blog_data, case_study_date),
        generate_header_section(),
        generate_article_header(blog_data, case_study_date, category),
        generate_summary_section(preview_data),
        generate_pdf_viewer_section(pdf_url),
        generate_vision_section(blog_data),
        generate_process_section(blog_data),
        generate_story_section(blog_data),
        generate_result_section(blog_data),
        generate_impact_section(blog_data),
        generate_footer_section(blog_data)
    ]
    
    return ''.join(html_parts)


async def fetch_case_study(identifier: str, by_slug: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch case study from database by ID or slug
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        if by_slug:
            query = """
                SELECT id, slug, case_study, status, type, date, keyword, preview, category,
                       editors_choice, redirect_url, pdf_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE slug = $1 AND isdeleted = FALSE
                LIMIT 1
            """
        else:
            query = """
                SELECT id, slug, case_study, status, type, date, keyword, preview, category,
                       editors_choice, redirect_url, pdf_url, isdeleted, created_at, updated_at
                FROM case_studies
                WHERE id = $1 AND isdeleted = FALSE
                LIMIT 1
            """
        
        case_study = await conn.fetchrow(query, identifier)
        await conn.close()
        
        if case_study:
            return {
                "id": str(case_study['id']),
                "slug": case_study['slug'],
                "blog": case_study['case_study'],
                "status": case_study['status'],
                "type": case_study['type'],
                "date": case_study['date'].isoformat() if case_study['date'] else None,
                "keyword": case_study['keyword'],
                "category": case_study['category'],
                "preview": case_study['preview'],
                "editors_choice": case_study['editors_choice'],
                "redirect_url": case_study['redirect_url'],
                "pdf_url": case_study['pdf_url'],
                "isdeleted": case_study['isdeleted'],
                "created_at": case_study['created_at'].isoformat() if case_study['created_at'] else None,
                "updated_at": case_study['updated_at'].isoformat() if case_study['updated_at'] else None
            }
        
        return None
        
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/case-study/{slug}", response_class=HTMLResponse)
async def get_case_study_by_slug(slug: str):
    """
    FastAPI route handler to serve case study by slug
    """
    case_study_data = await fetch_case_study(slug, by_slug=True)
    
    if not case_study_data:
        raise HTTPException(status_code=404, detail="Case study not found")
    
    if case_study_data.get('status') != 'published':
        raise HTTPException(status_code=404, detail="Case study not available")
    
    html_content = assemble_case_study_html(case_study_data)
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/case-study/id/{case_study_id}", response_class=HTMLResponse)
async def get_case_study_by_id(case_study_id: str):
    """
    FastAPI route handler to serve case study by ID
    """
    case_study_data = await fetch_case_study(case_study_id, by_slug=False)
    
    if not case_study_data:
        raise HTTPException(status_code=404, detail="Case study not found")
    
    if case_study_data.get('status') != 'published':
        raise HTTPException(status_code=404, detail="Case study not available")
    
    html_content = assemble_case_study_html(case_study_data)
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/download_proxy")
async def download_proxy(pdf: str, filename: str = "document.pdf"):
    """
    Proxy endpoint to download PDF files with proper headers
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(pdf)
            response.raise_for_status()
            
            return StreamingResponse(
                iter([response.content]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/pdf"
                }
            )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading PDF: {str(e)}")
    return HTMLResponse(content=html_content, status_code=200)