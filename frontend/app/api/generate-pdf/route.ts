/**
 * API Route: POST /api/generate-pdf
 *
 * Generates a professionally formatted PDF from markdown content
 * with color-coded headers, proper spacing, and section organization
 */

import { NextRequest, NextResponse } from 'next/server';
import { PDFDocument, rgb, StandardFonts, PDFFont, PDFPage } from 'pdf-lib';

// OptiMATE brand color (orange)
const PRIMARY_COLOR = rgb(0.906, 0.416, 0.157); // #e76a28
const TEXT_COLOR = rgb(0.1, 0.1, 0.1);
const DIM_TEXT_COLOR = rgb(0.4, 0.4, 0.4);
const CODE_BG_COLOR = rgb(0.95, 0.95, 0.95);

interface PDFContext {
  pdfDoc: PDFDocument;
  page: PDFPage;
  y: number;
  margin: number;
  pageWidth: number;
  pageHeight: number;
  maxWidth: number;
  regularFont: PDFFont;
  boldFont: PDFFont;
  monoFont: PDFFont;
  pageNumber: number;
}

export async function POST(request: NextRequest) {
  console.log('\n[API] POST /api/generate-pdf');

  try {
    const body = await request.json();
    const { markdown, jobId } = body;

    if (!markdown) {
      return NextResponse.json(
        { error: 'markdown content is required' },
        { status: 400 }
      );
    }

    // Create PDF document
    const pdfDoc = await PDFDocument.create();
    const regularFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const monoFont = await pdfDoc.embedFont(StandardFonts.Courier);

    const pageWidth = 595; // A4 width in points
    const pageHeight = 842; // A4 height in points
    const margin = 60;
    const maxWidth = pageWidth - 2 * margin;

    let context: PDFContext = {
      pdfDoc,
      page: pdfDoc.addPage([pageWidth, pageHeight]),
      y: pageHeight - margin,
      margin,
      pageWidth,
      pageHeight,
      maxWidth,
      regularFont,
      boldFont,
      monoFont,
      pageNumber: 1,
    };

    // Add title page
    context = addTitlePage(context, jobId);

    // Parse markdown and add content
    context = await addMarkdownContent(context, markdown);

    // Add page numbers to all pages
    addPageNumbers(pdfDoc, regularFont);

    // Serialize the PDF to bytes
    const pdfBytes = await pdfDoc.save();

    console.log('[API] ✓ PDF generated successfully');

    // Return PDF as a blob
    return new NextResponse(Buffer.from(pdfBytes), {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="optimateport-${jobId || 'result'}.pdf"`,
      },
    });
  } catch (error) {
    console.error('[API] Error generating PDF:', error);
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';

    return NextResponse.json(
      { error: 'Failed to generate PDF', details: errorMessage },
      { status: 500 }
    );
  }
}

/**
 * Add professional title page
 */
function addTitlePage(context: PDFContext, jobId: string): PDFContext {
  const { page, pageWidth, pageHeight, boldFont } = context;

  // OptiMATE Title
  const titleY = pageHeight - 200;
  page.drawText('Opti', {
    x: pageWidth / 2 - 80,
    y: titleY,
    size: 48,
    font: boldFont,
    color: TEXT_COLOR,
  });

  page.drawText('MATE', {
    x: pageWidth / 2,
    y: titleY,
    size: 48,
    font: boldFont,
    color: PRIMARY_COLOR,
  });

  // Subtitle
  page.drawText('Optimization Report', {
    x: pageWidth / 2 - 85,
    y: titleY - 50,
    size: 20,
    font: context.regularFont,
    color: DIM_TEXT_COLOR,
  });

  // Job ID
  if (jobId) {
    page.drawText(`Job ID: ${jobId}`, {
      x: pageWidth / 2 - 60,
      y: titleY - 100,
      size: 12,
      font: context.regularFont,
      color: DIM_TEXT_COLOR,
    });
  }

  // Date
  const date = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  page.drawText(date, {
    x: pageWidth / 2 - 50,
    y: titleY - 130,
    size: 12,
    font: context.regularFont,
    color: DIM_TEXT_COLOR,
  });

  // Decorative line
  page.drawLine({
    start: { x: context.margin, y: titleY - 160 },
    end: { x: pageWidth - context.margin, y: titleY - 160 },
    thickness: 2,
    color: PRIMARY_COLOR,
  });

  // Note about charts
  const noteY = 150;
  page.drawText('Note: Interactive charts and visualizations are available in the web version.', {
    x: context.margin,
    y: noteY,
    size: 10,
    font: context.regularFont,
    color: DIM_TEXT_COLOR,
  });

  // Start new page for content
  context.page = context.pdfDoc.addPage([context.pageWidth, context.pageHeight]);
  context.y = context.pageHeight - context.margin;
  context.pageNumber++;

  return context;
}

/**
 * Parse markdown and add formatted content
 */
async function addMarkdownContent(context: PDFContext, markdown: string): Promise<PDFContext> {
  const lines = markdown.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Check for headers
    if (line.startsWith('# ')) {
      context = checkAndAddNewPage(context, 60);
      context = addH1(context, line.substring(2));
      context.y -= 10;
    } else if (line.startsWith('## ')) {
      context = checkAndAddNewPage(context, 50);
      context = addH2(context, line.substring(3));
      context.y -= 8;
    } else if (line.startsWith('### ')) {
      context = checkAndAddNewPage(context, 40);
      context = addH3(context, line.substring(4));
      context.y -= 6;
    } else if (line.startsWith('```')) {
      // Code block
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      context = addCodeBlock(context, codeLines.join('\n'));
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      // Bullet point
      context = addBulletPoint(context, line.substring(2));
    } else if (line.trim().startsWith('|')) {
      // Table row - skip for simplicity (tables are complex in PDFs)
      continue;
    } else if (line.trim()) {
      // Regular paragraph
      context = addParagraph(context, line);
    } else {
      // Empty line - add spacing
      context.y -= 8;
    }
  }

  return context;
}

/**
 * Add H1 heading (large, orange)
 */
function addH1(context: PDFContext, text: string): PDFContext {
  const cleanText = cleanMarkdown(text);
  context.page.drawText(cleanText, {
    x: context.margin,
    y: context.y,
    size: 24,
    font: context.boldFont,
    color: PRIMARY_COLOR,
  });
  context.y -= 30;
  return context;
}

/**
 * Add H2 heading (medium, orange)
 */
function addH2(context: PDFContext, text: string): PDFContext {
  const cleanText = cleanMarkdown(text);
  context.page.drawText(cleanText, {
    x: context.margin,
    y: context.y,
    size: 18,
    font: context.boldFont,
    color: PRIMARY_COLOR,
  });
  context.y -= 24;
  return context;
}

/**
 * Add H3 heading (small, bold)
 */
function addH3(context: PDFContext, text: string): PDFContext {
  const cleanText = cleanMarkdown(text);
  context.page.drawText(cleanText, {
    x: context.margin,
    y: context.y,
    size: 14,
    font: context.boldFont,
    color: TEXT_COLOR,
  });
  context.y -= 20;
  return context;
}

/**
 * Add regular paragraph with word wrapping
 */
function addParagraph(context: PDFContext, text: string): PDFContext {
  const cleanText = cleanMarkdown(text);
  context = addWrappedText(context, cleanText, context.regularFont, 11, TEXT_COLOR, 14);
  context.y -= 6;
  return context;
}

/**
 * Add bullet point
 */
function addBulletPoint(context: PDFContext, text: string): PDFContext {
  const cleanText = cleanMarkdown(text);

  // Draw bullet
  context.page.drawText('•', {
    x: context.margin + 5,
    y: context.y,
    size: 11,
    font: context.regularFont,
    color: PRIMARY_COLOR,
  });

  // Draw text with indent
  const originalMargin = context.margin;
  context.margin += 20;
  context = addWrappedText(context, cleanText, context.regularFont, 11, TEXT_COLOR, 14);
  context.margin = originalMargin;
  context.y -= 4;

  return context;
}

/**
 * Add code block with background
 */
function addCodeBlock(context: PDFContext, code: string): PDFContext {
  context = checkAndAddNewPage(context, 100);

  const codeLines = code.split('\n');
  const lineHeight = 12;
  const padding = 10;
  const blockHeight = (codeLines.length * lineHeight) + (2 * padding);

  // Draw background
  context.page.drawRectangle({
    x: context.margin,
    y: context.y - blockHeight + padding,
    width: context.maxWidth,
    height: blockHeight,
    color: CODE_BG_COLOR,
  });

  context.y -= padding;

  // Draw code lines
  for (const line of codeLines) {
    context = checkAndAddNewPage(context, lineHeight + 10);

    context.page.drawText(line.substring(0, 80), { // Truncate long lines
      x: context.margin + padding,
      y: context.y,
      size: 9,
      font: context.monoFont,
      color: TEXT_COLOR,
    });
    context.y -= lineHeight;
  }

  context.y -= padding + 10;
  return context;
}

/**
 * Add wrapped text (handles line breaks)
 */
function addWrappedText(
  context: PDFContext,
  text: string,
  font: PDFFont,
  fontSize: number,
  color: any,
  lineHeight: number
): PDFContext {
  const words = text.split(' ');
  let currentLine = '';

  for (const word of words) {
    const testLine = currentLine + (currentLine ? ' ' : '') + word;
    const textWidth = font.widthOfTextAtSize(testLine, fontSize);

    if (textWidth > context.maxWidth && currentLine) {
      context = checkAndAddNewPage(context, lineHeight + 5);

      context.page.drawText(currentLine, {
        x: context.margin,
        y: context.y,
        size: fontSize,
        font: font,
        color: color,
      });
      context.y -= lineHeight;
      currentLine = word;
    } else {
      currentLine = testLine;
    }
  }

  // Draw remaining line
  if (currentLine) {
    context = checkAndAddNewPage(context, lineHeight + 5);

    context.page.drawText(currentLine, {
      x: context.margin,
      y: context.y,
      size: fontSize,
      font: font,
      color: color,
    });
    context.y -= lineHeight;
  }

  return context;
}

/**
 * Check if we need a new page and add one if needed
 */
function checkAndAddNewPage(context: PDFContext, requiredSpace: number): PDFContext {
  if (context.y < context.margin + requiredSpace) {
    context.page = context.pdfDoc.addPage([context.pageWidth, context.pageHeight]);
    context.y = context.pageHeight - context.margin;
    context.pageNumber++;
  }
  return context;
}

/**
 * Add page numbers to all pages
 */
function addPageNumbers(pdfDoc: PDFDocument, font: PDFFont): void {
  const pages = pdfDoc.getPages();
  const totalPages = pages.length;

  pages.forEach((page, index) => {
    if (index === 0) return; // Skip title page

    const pageNum = index;
    const text = `Page ${pageNum} of ${totalPages - 1}`;
    const textWidth = font.widthOfTextAtSize(text, 10);

    page.drawText(text, {
      x: (page.getWidth() - textWidth) / 2,
      y: 30,
      size: 10,
      font: font,
      color: DIM_TEXT_COLOR,
    });
  });
}

/**
 * Clean markdown formatting from text
 */
function cleanMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1') // Bold
    .replace(/\*(.*?)\*/g, '$1') // Italic
    .replace(/`(.*?)`/g, '$1') // Inline code
    .replace(/\$(.*?)\$/g, '$1') // Math
    .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Links
    .trim();
}
