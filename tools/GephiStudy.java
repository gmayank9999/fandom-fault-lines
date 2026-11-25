import java.awt.Color;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;
import org.gephi.graph.api.*;
import org.gephi.io.importer.api.*;
import org.gephi.io.processor.plugin.DefaultProcessor;
import org.gephi.io.exporter.api.ExportController;
import org.gephi.io.exporter.preview.SVGExporter;
import org.apache.batik.transcoder.TranscoderInput;
import org.apache.batik.transcoder.TranscoderOutput;
import org.apache.batik.transcoder.image.PNGTranscoder;
import org.gephi.layout.plugin.forceAtlas2.ForceAtlas2;
import org.gephi.preview.api.*;
import org.gephi.preview.types.EdgeColor;
import org.gephi.project.api.*;
import org.gephi.statistics.plugin.Degree;
import org.gephi.statistics.plugin.PageRank;
import org.openide.util.Lookup;

/** Native Gephi verification and two-workspace project generation.
 * Args: full.gexf focus.gexf output-stem expected-nodes expected-edges expected-weight
 * Uses the official Gephi Toolkit 0.11.3, not desktop input automation.
 */
public class GephiStudy {
    static Column column(Table table, String title) {
        for (Column column : table) if (column.getTitle().equals(title)) return column;
        throw new IllegalArgumentException("Missing imported attribute: " + title);
    }

    public static void main(String[] args) {
        try { run(args); }
        catch (Throwable failure) { failure.printStackTrace(); System.exit(1); }
    }

    public static void run(String[] args) throws Exception {
        Locale.setDefault(Locale.US);
        System.setProperty("java.awt.headless", "true");
        ProjectController projects = Lookup.getDefault().lookup(ProjectController.class);
        ImportController imports = Lookup.getDefault().lookup(ImportController.class);
        GraphController graphs = Lookup.getDefault().lookup(GraphController.class);
        ExportController exports = Lookup.getDefault().lookup(ExportController.class);
        Project project = projects.newProject();
        projects.renameProject(project, new File(args[2]).getName());
        Workspace full = projects.getCurrentWorkspace();
        Container container = imports.importFile(new File(args[0]));
        container.getLoader().setEdgeDefault(EdgeDirectionDefault.DIRECTED);
        container.getLoader().setAllowAutoNode(false);
        imports.process(container, new DefaultProcessor(), full);
        projects.renameWorkspace(full, "FULL — verified metrics");
        GraphModel gm = graphs.getGraphModel(full);
        DirectedGraph graph = gm.getDirectedGraph();
        int n = graph.getNodeCount(), m = graph.getEdgeCount();
        double weight = 0;
        for (Edge edge : graph.getEdges()) weight += edge.getWeight();
        if (n != Integer.parseInt(args[3]) || m != Integer.parseInt(args[4]) ||
                Math.abs(weight - Double.parseDouble(args[5])) > 0.001)
            throw new IllegalStateException("Gephi import differs from Python node/edge/weight totals");
        int degreeMismatches = 0;
        Column inDegree = column(gm.getNodeTable(), "in_degree");
        Column outDegree = column(gm.getNodeTable(), "out_degree");
        Column pythonRank = column(gm.getNodeTable(), "pagerank");
        for (Node node : graph.getNodes()) {
            if (((Number)node.getAttribute(inDegree)).intValue() != graph.getInDegree(node) ||
                ((Number)node.getAttribute(outDegree)).intValue() != graph.getOutDegree(node)) degreeMismatches++;
        }
        if (degreeMismatches != 0) throw new IllegalStateException("Directed degree mismatch");
        Degree degrees = new Degree();
        degrees.execute(gm);
        PageRank pr = new PageRank();
        pr.setDirected(true);
        pr.setUseEdgeWeight(true);
        pr.setProbability(0.85);
        pr.setEpsilon(1e-8);
        pr.execute(gm);
        double prSum = 0, prDifference = 0;
        for (Node node : graph.getNodes()) {
            double value = ((Number)node.getAttribute(PageRank.PAGERANK)).doubleValue();
            prSum += value;
            prDifference += Math.abs(value - ((Number)node.getAttribute(pythonRank)).doubleValue());
        }
        if (Math.abs(prSum - 1) > 0.001) throw new IllegalStateException("Invalid PageRank normalization");

        Workspace focus = projects.newWorkspace(project);
        projects.openWorkspace(focus);
        Container focusInput = imports.importFile(new File(args[1]));
        focusInput.getLoader().setEdgeDefault(EdgeDirectionDefault.DIRECTED);
        imports.process(focusInput, new DefaultProcessor(), focus);
        projects.renameWorkspace(focus, "FOCUS — display only, ForceAtlas2");
        GraphModel focusModel = graphs.getGraphModel(focus);
        DirectedGraph display = focusModel.getDirectedGraph();
        // Display-only repeated-reply backbone. The full workspace is untouched.
        for (Edge edge : display.getEdges().toArray()) if (edge.getWeight() < 2) display.removeEdge(edge);
        for (Node node : display.getNodes().toArray()) if (display.getDegree(node) == 0) display.removeNode(node);
        if (display.getNodeCount() == 0) throw new IllegalStateException("No repeated-reply display backbone");
        ForceAtlas2 layout = new ForceAtlas2(null);
        layout.setGraphModel(focusModel);
        layout.resetPropertiesValues();
        layout.setInitialisationSeed(42);
        layout.setThreadsCount(1);
        layout.setBarnesHutOptimize(true);
        layout.setScalingRatio(8.0);
        layout.setGravity(1.0);
        layout.setEdgeWeightInfluence(0.5);
        layout.setLinLogMode(true);
        layout.setAdjustSizes(false);
        layout.initAlgo();
        for (int step = 0; step < 400 && layout.canAlgo(); step++) layout.goAlgo();
        layout.endAlgo();
        float xmin = Float.POSITIVE_INFINITY, xmax = Float.NEGATIVE_INFINITY;
        float ymin = Float.POSITIVE_INFINITY, ymax = Float.NEGATIVE_INFINITY;
        for (Node node : display.getNodes()) {
            xmin = Math.min(xmin, node.x()); xmax = Math.max(xmax, node.x());
            ymin = Math.min(ymin, node.y()); ymax = Math.max(ymax, node.y());
        }
        float scale = 1800f / Math.max(xmax - xmin, ymax - ymin);
        Column incomingStrength = column(focusModel.getNodeTable(), "in_strength");
        for (Node node : display.getNodes()) {
            node.setX((node.x() - (xmin + xmax) / 2f) * scale);
            node.setY((node.y() - (ymin + ymax) / 2f) * scale);
            // Explicit sizes avoid GEXF import-time visualization scaling.
            double incoming = ((Number)node.getAttribute(incomingStrength)).doubleValue();
            node.setSize((float)(2 + 0.7 * Math.log1p(incoming)));
        }
        PreviewController preview = Lookup.getDefault().lookup(PreviewController.class);
        PreviewProperties props = preview.getModel(focus).getProperties();
        props.putValue(PreviewProperty.SHOW_NODE_LABELS, false);
        props.putValue(PreviewProperty.BACKGROUND_COLOR, new Color(252, 252, 251));
        props.putValue(PreviewProperty.EDGE_COLOR, new EdgeColor(new Color(110, 115, 125)));
        props.putValue(PreviewProperty.EDGE_OPACITY, 28);
        props.putValue(PreviewProperty.EDGE_THICKNESS, 0.5f);
        props.putValue(PreviewProperty.EDGE_USE_WEIGHT, false);
        props.putValue(PreviewProperty.EDGE_CURVED, false);
        props.putValue(PreviewProperty.ARROW_SIZE, 1f);
        props.putValue(PreviewProperty.NODE_BORDER_WIDTH, 0.1f);
        props.putValue(PreviewProperty.NODE_SCALE_FACTOR, 1f);
        preview.refreshPreview(focus);
        // Gephi's G2D PNG path needs a screen device. SVG + Batik rasterization
        // remains headless and also provides a publication-quality vector file.
        SVGExporter svg = (SVGExporter)exports.getExporter("svg");
        svg.setWorkspace(focus);
        svg.setMargin(40f);
        File svgFile = new File(args[2] + ".svg");
        exports.exportFile(svgFile, svg);
        // The exporter fits its viewBox tightly even when a margin is requested.
        // Pad the viewBox so peripheral nodes are not flush with the image edge.
        String svgText = Files.readString(svgFile.toPath());
        java.util.regex.Matcher bounds = java.util.regex.Pattern.compile("viewBox=\"([^\"]+)\"").matcher(svgText);
        if (!bounds.find()) throw new IllegalStateException("SVG export has no viewBox");
        String[] box = bounds.group(1).trim().split("\\s+");
        double pad = 60;
        String padded = String.format(java.util.Locale.ROOT, "viewBox=\"%f %f %f %f\"",
            Double.parseDouble(box[0]) - pad, Double.parseDouble(box[1]) - pad,
            Double.parseDouble(box[2]) + 2 * pad, Double.parseDouble(box[3]) + 2 * pad);
        Files.writeString(svgFile.toPath(), bounds.replaceFirst(padded));
        PNGTranscoder raster = new PNGTranscoder() {
            @Override public void writeImage(java.awt.image.BufferedImage image, TranscoderOutput output)
                    throws org.apache.batik.transcoder.TranscoderException {
                try { javax.imageio.ImageIO.write(image, "png", output.getOutputStream()); }
                catch (java.io.IOException failure) { throw new org.apache.batik.transcoder.TranscoderException(failure); }
            }
        };
        raster.addTranscodingHint(PNGTranscoder.KEY_WIDTH, 1800f);
        raster.addTranscodingHint(PNGTranscoder.KEY_HEIGHT, 1800f);
        raster.addTranscodingHint(PNGTranscoder.KEY_BACKGROUND_COLOR, new Color(252, 252, 251));
        try (java.io.OutputStream stream = Files.newOutputStream(Path.of(args[2] + ".png"))) {
            raster.transcode(new TranscoderInput(svgFile.toURI().toString()), new TranscoderOutput(stream));
        }
        File saved = new File(args[2] + ".gephi");
        projects.saveProject(project, saved);
        projects.closeCurrentProject();
        Project reopened = projects.openProject(saved);
        if (reopened.getWorkspaces().size() != 2) throw new IllegalStateException("Project reload lost workspaces");
        boolean foundFull = false;
        for (Workspace ws : reopened.getWorkspaces()) {
            Graph g = graphs.getGraphModel(ws).getGraph();
            if (g.getNodeCount() == n && g.getEdgeCount() == m) foundFull = true;
        }
        if (!foundFull) throw new IllegalStateException("Full network absent after .gephi reload");
        String json = String.format("{\"toolkit\":\"0.11.3\",\"nodes\":%d,\"edges\":%d,\"reply_weight\":%.0f,\"degree_mismatches\":%d,\"pagerank_sum\":%.10f,\"pagerank_l1_difference_python\":%.10f,\"project_reopened\":true,\"workspaces\":2,\"layout\":\"ForceAtlas2\",\"iterations\":400,\"seed\":42,\"threads\":1,\"scaling\":8,\"gravity\":1,\"edge_weight_influence\":0.5,\"linlog\":true}", n, m, weight, degreeMismatches, prSum, prDifference);
        json = json.substring(0, json.length() - 1) + String.format(",\"display_nodes\":%d,\"display_edges\":%d,\"display_filter\":\"focus graph; directed weight >= 2; isolates removed\"}", display.getNodeCount(), display.getEdgeCount());
        Files.writeString(Path.of(args[2] + "_validation.json"), json);
        System.out.println(json);
        projects.closeCurrentProject();
        System.exit(0);
    }
}
