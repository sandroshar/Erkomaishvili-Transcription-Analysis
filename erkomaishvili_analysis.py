import xml.etree.ElementTree as ET
import pandas as pd
import music21
import os
from typing import List, Dict, Set, Tuple
from collections import defaultdict

class ChantAnalyzer:
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.score = music21.converter.parse(xml_path)
        self.voices = self.extract_voices()
        self.gch_id = self.extract_gch_id(xml_path)
        
    def extract_gch_id(self, filepath: str) -> str:
        """Extract GCH ID from filename."""
        filename = os.path.basename(filepath)
        return filename.split('_')[1]
        
    def extract_voices(self) -> Dict[str, music21.stream.Part]:
        """Extract the three voices from the score."""
        parts = self.score.parts
        return {
            'top': parts[0],
            'middle': parts[1],
            'bass': parts[2]
        }
        
    def get_notes_in_voice(self, voice: music21.stream.Part) -> List[music21.note.Note]:
        """Extract all notes from a voice part."""
        return [n for n in voice.recurse().notes if isinstance(n, music21.note.Note)]
        
    def extract_mode(self, notes: List[music21.note.Note], center_note: music21.note.Note) -> str:
        """Extract mode starting from center note."""
        if not notes:
            return ""
            
        # Get unique pitch classes
        pitch_classes = set(n.pitch.name for n in notes)
        
        # If center note pitch class isn't in our set, add it
        center_pc = center_note.pitch.name
        pitch_classes.add(center_pc)
        
        try:
            # Sort pitches starting from center
            sorted_pitches = sorted(pitch_classes, 
                                  key=lambda x: (music21.pitch.Pitch(x).ps - music21.pitch.Pitch(center_pc).ps) % 12)
            
            # Rotate list to start from center pitch
            start_idx = sorted_pitches.index(center_pc)
            mode = sorted_pitches[start_idx:] + sorted_pitches[:start_idx]
            
            return " ".join(mode)
        except Exception as e:
            print(f"Warning: Error processing mode: {str(e)}")
            print(f"Pitch classes: {pitch_classes}")
            print(f"Center pitch: {center_pc}")
            return ""
    
    def get_full_modes(self) -> Dict[str, str]:
        """Get full modes for all voices and combined."""
        all_notes = defaultdict(list)
        modes = {}
        
        # Get notes and final notes for each voice
        final_notes = {}
        for voice_name, voice in self.voices.items():
            notes = self.get_notes_in_voice(voice)
            all_notes[voice_name] = notes
            if notes:  # Only if voice has notes
                final_notes[voice_name] = notes[-1]
                modes[f'{voice_name}_mode'] = self.extract_mode(notes, final_notes[voice_name])
        
        # Combined voices mode
        all_voice_notes = []
        for notes in all_notes.values():
            all_voice_notes.extend(notes)
            
        if all_voice_notes and 'bass' in final_notes:
            modes['combined_mode'] = self.extract_mode(all_voice_notes, final_notes['bass'])
        
        return modes
        
    def get_mukhli_modes(self) -> List[Dict[str, str]]:
        """Get modes for each mukhli (measure)."""
        mukhli_modes = []
        
        try:
            # Get measures from the first voice (they should be aligned)
            measures = list(self.voices['top'].measures(1, None))  # Convert to list for easier handling
            if not measures:
                print(f"Warning: No measures found in {self.xml_path}")
                return []
                
            for i, measure in enumerate(measures, 1):
                measure_data = {}
                
                # For each voice in the measure
                for voice_name, voice in self.voices.items():
                    try:
                        # Find corresponding measure in this voice
                        voice_measure = voice.measure(i)
                        if not voice_measure:
                            print(f"Warning: No measure {i} found in {voice_name} voice")
                            continue
                            
                        notes = self.get_notes_in_voice(voice_measure)
                        if not notes:
                            print(f"Warning: No notes found in measure {i} of {voice_name} voice")
                            continue
                            
                        # Get last note or bottom note of final fifth
                        final_note = notes[-1]
                        if voice_name != 'bass':
                            # Check for fifth with bass
                            bass_measure = self.voices['bass'].measure(i)
                            if bass_measure:
                                bass_notes = self.get_notes_in_voice(bass_measure)
                                if bass_notes:
                                    try:
                                        interval = music21.interval.Interval(bass_notes[-1], final_note)
                                        if interval.name == 'P5':
                                            final_note = bass_notes[-1]
                                    except Exception as e:
                                        print(f"Warning: Error checking interval in measure {i}: {str(e)}")
                        
                        measure_data[f'{voice_name}_mode'] = self.extract_mode(notes, final_note)
                    except Exception as e:
                        print(f"Warning: Error processing {voice_name} voice in measure {i}: {str(e)}")
                        continue
                
                # Combined mode for measure
                try:
                    all_notes = []
                    for voice_name, voice in self.voices.items():
                        measure_voice = voice.measure(i)
                        if measure_voice:
                            all_notes.extend(self.get_notes_in_voice(measure_voice))
                    
                    if all_notes:
                        bass_measure = self.voices['bass'].measure(i)
                        bass_notes = self.get_notes_in_voice(bass_measure) if bass_measure else []
                        center_note = bass_notes[-1] if bass_notes else all_notes[-1]
                        measure_data['combined_mode'] = self.extract_mode(all_notes, center_note)
                except Exception as e:
                    print(f"Warning: Error processing combined mode for measure {i}: {str(e)}")
                
                mukhli_modes.append(measure_data)
                
            return mukhli_modes
        except Exception as e:
            print(f"Error processing mukhli modes: {str(e)}")
            return []
            
        for i, measure in enumerate(measures, 1):
            measure_data = {}
            
            # For each voice in the measure
            for voice_name, voice in self.voices.items():
                # Find corresponding measure in this voice
                voice_measure = voice.measure(i)
                if not voice_measure:
                    continue
                    
                notes = self.get_notes_in_voice(voice_measure)
                if not notes:
                    continue
                    
                # Get last note or bottom note of final fifth
                final_note = notes[-1]
                if voice_name != 'bass':
                    # Check for fifth with bass
                    bass_measure = self.voices['bass'].measure(i)
                    if bass_measure:
                        bass_notes = self.get_notes_in_voice(bass_measure)
                        if bass_notes:
                            interval = music21.interval.Interval(bass_notes[-1], final_note)
                            if interval.name == 'P5':
                                final_note = bass_notes[-1]
                
                measure_data[f'{voice_name}_mode'] = self.extract_mode(notes, final_note)
            
            # Combined mode for measure
            all_notes = []
            for voice_name, voice in self.voices.items():
                measure_voice = voice.measure(i)
                if measure_voice:
                    all_notes.extend(self.get_notes_in_voice(measure_voice))
            
            if all_notes:
                bass_measure = self.voices['bass'].measure(i)
                bass_notes = self.get_notes_in_voice(bass_measure) if bass_measure else []
                center_note = bass_notes[-1] if bass_notes else all_notes[-1]
                measure_data['combined_mode'] = self.extract_mode(all_notes, center_note)
            
            mukhli_modes.append(measure_data)
            
        return mukhli_modes
    
    def find_melodic_patterns(self) -> Dict[str, List[str]]:
        """Find specified melodic patterns and record their locations."""
        patterns = defaultdict(list)
        
        def check_consecutive_notes(notes: List[music21.note.Note], 
                                  interval_name: str) -> List[Tuple[int, int]]:
            """Find consecutive notes forming specified interval."""
            results = []
            for i in range(len(notes)-1):
                interval = music21.interval.Interval(notes[i], notes[i+1])
                if interval.name == interval_name:
                    # Get QNR numbers from the notes (second lyric is QNR)
                    if len(notes[i].lyrics) > 1 and len(notes[i+1].lyrics) > 1:
                        qnr1 = notes[i].lyrics[1].text
                        qnr2 = notes[i+1].lyrics[1].text
                        results.append((qnr1, qnr2))
            return results
        
        def check_tetrachord(notes: List[music21.note.Note], start_idx: int) -> Tuple[str, bool]:
            """Check if notes starting at start_idx form a tetrachord."""
            if start_idx + 3 >= len(notes):  # Need at least 4 notes
                return None, False
                
            # Get intervals between consecutive notes in semitones
            intervals = []
            for i in range(3):
                interval = music21.interval.Interval(notes[start_idx + i], 
                                                   notes[start_idx + i + 1])
                intervals.append(interval.semitones)
                
            # Check for fifth if we have enough notes
            has_fifth = False
            if start_idx + 4 < len(notes):
                fifth_interval = music21.interval.Interval(notes[start_idx],
                                                         notes[start_idx + 4])
                has_fifth = fifth_interval.name == 'P5'
            
            # Match interval patterns
            if intervals == [2, 2, 1]:  # Major tetrachord
                return 'major', has_fifth
            elif intervals == [2, 1, 2]:  # Minor tetrachord
                return 'minor', has_fifth
            elif intervals == [1, 3, 1]:  # Phrygian tetrachord
                return 'phrygian', has_fifth
            elif intervals == [2, 2, 2]:  # Lydian tetrachord
                return 'lydian', has_fifth
            
            return None, False
            
        # Check each voice for melodic patterns
        for voice_idx, (voice_name, voice) in enumerate(self.voices.items(), 1):
            notes = self.get_notes_in_voice(voice)
            
            # Melodic intervals
            for pattern, interval in [
                ('P4', 'P4'),
                ('M3', 'M3'),
                ('m3', 'm3')
            ]:
                locations = check_consecutive_notes(notes, interval)
                for idx, (qnr1, qnr2) in enumerate(locations, 1):
                    patterns[pattern].append(
                        f"{idx}.{self.gch_id}.{voice_idx}.{qnr1}-{qnr2}")
            
            # Tetrachords
            for i in range(len(notes)):
                tetrachord_type, has_fifth = check_tetrachord(notes, i)
                if tetrachord_type:
                    # Get QNR numbers for the tetrachord
                    if all(len(n.lyrics) > 1 for n in notes[i:i+4]):
                        qnrs = [n.lyrics[1].text for n in notes[i:i+4]]
                        pattern_key = f'{tetrachord_type}_tetrachord'
                        if has_fifth and i+4 < len(notes) and len(notes[i+4].lyrics) > 1:
                            pattern_key += '_fifth'
                            qnrs.append(notes[i+4].lyrics[1].text)
                            
                        # Only add if not followed by fifth (unless we're specifically looking for fifth)
                        if has_fifth:
                            if pattern_key not in patterns:
                                patterns[pattern_key] = []
                            patterns[pattern_key].append(
                                f"{len(patterns[pattern_key])+1}.{self.gch_id}.{voice_idx}.{qnrs[0]}-{qnrs[-1]}")
                        else:
                            # Check if the next note forms a fifth
                            if i + 4 < len(notes):
                                next_interval = music21.interval.Interval(notes[i], notes[i+4])
                                if next_interval.name != 'P5':
                                    if pattern_key not in patterns:
                                        patterns[pattern_key] = []
                                    patterns[pattern_key].append(
                                        f"{len(patterns[pattern_key])+1}.{self.gch_id}.{voice_idx}.{qnrs[0]}-{qnrs[-1]}")
        
        return patterns

def process_chant_files(directory: str):
    """Process all chant files in directory and generate CSVs."""
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    full_modes_data = []
    mukhli_modes_data = []
    patterns_data = []
    chant_numbers = []  # Store actual chant numbers from filenames
    
    max_mukhlis = 0
    
    # First pass to determine maximum number of mukhlis
    print("Analyzing files to determine structure...")
    for filename in sorted(os.listdir(directory)):  # Sort to process in order
        if filename.endswith('.xml'):
            print(f"Pre-processing {filename}")
            analyzer = ChantAnalyzer(os.path.join(directory, filename))
            mukhlis = len(analyzer.get_mukhli_modes())
            max_mukhlis = max(max_mukhlis, mukhlis)
    
    print(f"\nProcessing files...")
    # Second pass to process files
    for filename in sorted(os.listdir(directory)):  # Sort to process in order
        if filename.endswith('.xml'):
            print(f"Analyzing {filename}")
            filepath = os.path.join(directory, filename)
            analyzer = ChantAnalyzer(filepath)
            
            # Extract chant number from filename
            chant_num = filename.split('_')[1]  # Gets '001' from 'GCH_001_...'
            chant_numbers.append(chant_num)
            
            # Full modes
            modes = analyzer.get_full_modes()
            full_modes_data.append(modes)
            
            # Mukhli modes
            mukhli_modes = analyzer.get_mukhli_modes()
            # Pad with None for consistent columns
            while len(mukhli_modes) < max_mukhlis:
                mukhli_modes.append({})
            mukhli_modes_data.append(mukhli_modes)
            
            # Patterns
            patterns = analyzer.find_melodic_patterns()
            patterns_data.append(patterns)
    
    print("\nGenerating output files...")
    # Create DataFrames and save to CSV
    # Full modes
    df_full = pd.DataFrame(full_modes_data)
    df_full.insert(0, 'chant_number', chant_numbers)  # Insert chant numbers as first column
    df_full.to_csv('output/full_modes.csv', index=False)
    print("Created full_modes.csv")
    
    # Mukhli modes
    mukhli_columns = []
    for i in range(max_mukhlis):
        for voice in ['combined', 'top', 'middle', 'bass']:
            mukhli_columns.append(f'mukhli_{i+1}_{voice}_mode')
    
    df_mukhli = pd.DataFrame(columns=['chant_number'] + mukhli_columns)
    for idx, mukhli_data in enumerate(mukhli_modes_data):
        row_data = {'chant_number': chant_numbers[idx]}  # Use actual chant number
        for i, measure in enumerate(mukhli_data):
            for voice in ['combined', 'top', 'middle', 'bass']:
                col = f'mukhli_{i+1}_{voice}_mode'
                row_data[col] = measure.get(f'{voice}_mode')
        df_mukhli.loc[idx] = row_data
    
    df_mukhli.to_csv('output/mukhli_modes.csv', index=False)
    print("Created mukhli_modes.csv")
    
    # Patterns
    df_patterns = pd.DataFrame(patterns_data)
    df_patterns.insert(0, 'chant_number', chant_numbers)  # Add actual chant numbers
    df_patterns.to_csv('output/musical_events.csv', index=False)
    print("Created musical_events.csv")
    print("\nAnalysis complete!")
    
    df_mukhli.to_csv('output/mukhli_modes.csv', index=False)
    print("Created mukhli_modes.csv")
    
    # Patterns
    df_patterns = pd.DataFrame(patterns_data)
    df_patterns.insert(0, 'chant_number', chant_numbers)  # Add chant numbers
    df_patterns.to_csv('output/musical_events.csv', index=False)
    print("Created musical_events.csv")
    print("\nAnalysis complete!")

if __name__ == "__main__":
    if os.path.exists("data"):
        process_chant_files("data")
    else:
        print("Error: 'data' folder not found. Please create a 'data' folder and place your XML files there.")