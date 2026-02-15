/**
 * API Route: POST /api/generate-pdf
 *
 * Generates a PDF from markdown content
 */

import { NextRequest, NextResponse } from 'next/server';
import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import { marked } from 'marked';

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
    const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
    const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    const monoFont = await pdfDoc.embedFont(StandardFonts.Courier);

    // Parse markdown to plain text (strip formatting for PDF)
    const htmlContent = await marked(markdown);

    // Convert HTML to plain text (remove tags)
    const plainText = htmlContent
      .replace(/<[^>]*>/g, '') // Remove HTML tags
      .replace(/&nbsp;/g, ' ')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .trim();

    // Add pages and write content
    const pageWidth = 595; // A4 width in points
    const pageHeight = 842; // A4 height in points
    const margin = 50;
    const maxWidth = pageWidth - 2 * margin;
    const lineHeight = 14;
    const fontSize = 11;

    let page = pdfDoc.addPage([pageWidth, pageHeight]);
    let y = pageHeight - margin;

    // Split text into lines that fit the page width
    const lines = plainText.split('\n');

    for (const line of lines) {
      // Check if we need a new page
      if (y < margin + lineHeight) {
        page = pdfDoc.addPage([pageWidth, pageHeight]);
        y = pageHeight - margin;
      }

      // Wrap long lines
      const words = line.split(' ');
      let currentLine = '';

      for (const word of words) {
        const testLine = currentLine + (currentLine ? ' ' : '') + word;
        const textWidth = font.widthOfTextAtSize(testLine, fontSize);

        if (textWidth > maxWidth && currentLine) {
          // Draw current line
          page.drawText(currentLine, {
            x: margin,
            y: y,
            size: fontSize,
            font: font,
            color: rgb(0, 0, 0),
          });
          y -= lineHeight;
          currentLine = word;

          // Check if we need a new page
          if (y < margin + lineHeight) {
            page = pdfDoc.addPage([pageWidth, pageHeight]);
            y = pageHeight - margin;
          }
        } else {
          currentLine = testLine;
        }
      }

      // Draw remaining line
      if (currentLine) {
        page.drawText(currentLine, {
          x: margin,
          y: y,
          size: fontSize,
          font: font,
          color: rgb(0, 0, 0),
        });
        y -= lineHeight;
      }

      // Add extra space between paragraphs
      if (!line.trim()) {
        y -= lineHeight / 2;
      }
    }

    // Add header with job ID
    const firstPage = pdfDoc.getPages()[0];
    firstPage.drawText(`Optima Optimization Report - ${jobId || 'N/A'}`, {
      x: margin,
      y: pageHeight - 30,
      size: 16,
      font: boldFont,
      color: rgb(0.2, 0.4, 0.8),
    });

    // Serialize the PDF to bytes
    const pdfBytes = await pdfDoc.save();

    // Return PDF as a blob
    return new NextResponse(Buffer.from(pdfBytes), {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="optima-report-${jobId || 'result'}.pdf"`,
      },
    });
  } catch (error: any) {
    console.error('[API] Error generating PDF:', error.message);

    return NextResponse.json(
      { error: 'Failed to generate PDF', details: error.message },
      { status: 500 }
    );
  }
}
