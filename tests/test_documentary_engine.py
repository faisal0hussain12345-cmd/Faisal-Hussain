import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from banna.documentary_engine import card_anchor, _build_world, _draw_overlay
from banna.annotations import make_paper_tracked, text_underline_world, text_circle_world, draw_wobble_circle
from banna.map_board import draw_coordinate_grid, render_map_panel, annotate_map_image
from banna.vintage import vintage_frame
from banna.timing import estimate_word_times, narration_timeline, align_scenes_to_words
from unittest.mock import patch

class DocumentaryEngineTests(unittest.TestCase):
    def test_overlay_draws_skill_annotations_without_error(self):
        frame=Image.new("RGB",(1920,1080),(16,26,44))
        scene={"title":"THE ARCHIVE","year":"1914","stamp":"TOP SECRET","tags":["SARAJEVO","CASE FILE"],"thesis":"The chain reaction mattered"}
        _draw_overlay(frame,scene,1.5,5.0,0,3)
        self.assertEqual(frame.size,(1920,1080))

    def test_rotated_card_anchor(self):
        card={"x":100,"y":100,"w":200,"h":100,"rotation":0}
        self.assertEqual(card_anchor(card,0,-0.5),(100.0,50.0))
        self.assertEqual(card_anchor(card,0.5,0),(200.0,100.0))
    def test_anchor_rejects_out_of_range(self):
        with self.assertRaises(ValueError): card_anchor({"x":0,"y":0,"w":1,"h":1},.6,0)
    def test_tracked_paper_geometry(self):
        im,meta=make_paper_tracked(["CONFIDENTIAL","ARCHIVE NOTE"])
        self.assertEqual(len(meta["lines"]),2)
        card={"x":500,"y":300,"w":1000,"h":600,"rotation":0}
        a,b=text_underline_world(card,meta,0)
        self.assertLess(a[0],b[0])
        self.assertEqual(len(text_circle_world(card,meta,1)),4)
        draw_wobble_circle(__import__("PIL").ImageDraw.Draw(im), (10,10,300,100))
    def test_map_image_annotations(self):
        base=Image.new("RGB",(500,300),(70,80,90))
        out=annotate_map_image(base,"SARajevo", [{"x":0.3,"y":0.4,"label":"A"},{"x":0.7,"y":0.6,"label":"B"}])
        self.assertEqual(out.size,(500,300))

    def test_map_scene_resolves_without_gemini(self):
        from banna.images import resolve_scene_images
        with TemporaryDirectory() as temp:
            root=Path(temp)
            paths=resolve_scene_images({"scenes":[{"id":"map","map_locations":[{"x":0.4,"y":0.5,"label":"CITY"}]}]},root/"photos",root/"generated","unused")
            self.assertTrue(paths[0].is_file())
            self.assertTrue((root/"generated"/"map_map_grid.jpg").is_file())

    def test_map_grid_and_pin_validation(self):
        im=Image.new("RGB",(300,200),"navy")
        self.assertEqual(draw_coordinate_grid(im).size,(300,200))
        with self.assertRaises(ValueError): render_map_panel("test",[{"x":1.2,"y":.5}])
        self.assertEqual(render_map_panel("test",[{"x":.5,"y":.5,"label":"X"}]).size,(1600,900))

    def test_continuous_board_renders_a_video_file(self):
        from banna.documentary_engine import render_continuous_board
        with TemporaryDirectory() as temp:
            root=Path(temp)
            photo=root/"still.png"
            Image.new("RGB",(320,180),(80,90,110)).save(photo)
            out=root/"board.mp4"
            render_continuous_board([photo],[{"title":"TEST EVIDENCE"}],[1.0],out,320,180,2,quality=30)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size,1000)

    def test_parallel_board_render_assembles_chunks(self):
        from banna.documentary_engine import render_continuous_board
        with TemporaryDirectory() as temp:
            root=Path(temp); photo=root/"still.png"
            Image.new("RGB",(320,180),(90,80,70)).save(photo)
            out=root/"parallel.mp4"
            render_continuous_board([photo],[{"title":"PARALLEL"}],[1.0],out,320,180,2,quality=30,workers=2)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size,1000)

    def test_vintage_insert_encodes_video(self):
        from banna.vintage import render_vintage_clip
        with TemporaryDirectory() as temp:
            out=Path(temp)/"vintage.mp4"
            render_vintage_clip("TEST INSERT",1.0,out,fps=2)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size,1000)

    def test_vintage_still_is_1080p(self):
        self.assertEqual(vintage_frame(.2,2,"Turning point").size,(1920,1080))

    def test_timeline_preserves_requested_scene_count(self):
        with patch("banna.timing.probe_audio", return_value={"duration": 10.0}), patch("banna.timing.silence_ranges", return_value=[(1.0,1.2),(3.0,3.2),(5.0,5.2),(7.0,7.2)]):
            result=narration_timeline(Path("unused.mp3"),5)
        self.assertEqual(len(result["scene_durations"]),5)
        self.assertAlmostEqual(sum(result["scene_durations"]),10.0)
        self.assertTrue(all(x>=0.5 for x in result["scene_durations"]))

    def test_scene_cues_align_to_exact_transcribed_word(self):
        words=[{"word":"first","start":0.1,"end":0.4},{"word":"turning","start":4.2,"end":4.5},{"word":"point","start":4.5,"end":4.8},{"word":"after","start":5.0,"end":5.2}]
        scenes=[{"title":"Opening"},{"title":"Turning Point","trigger_words":"turning point"}]
        result=align_scenes_to_words(words,scenes,10.0,[0.0,5.0,10.0])
        self.assertAlmostEqual(result[1],4.2)
        self.assertEqual(result[-1],10.0)

    def test_estimated_word_alignment_is_monotonic(self):
        rows=estimate_word_times("One two three",3)
        self.assertEqual(len(rows),3)
        self.assertAlmostEqual(rows[0]["start"],0)
        self.assertAlmostEqual(rows[-1]["end"],3)
        self.assertTrue(all(a["end"]<=b["start"]+1e-8 for a,b in zip(rows,rows[1:])))

if __name__=="__main__": unittest.main()
