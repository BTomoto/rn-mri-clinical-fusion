"""Hand-computed GLCM, invariant processing and truthful cache/failure checks."""
from pathlib import Path
import sys,tempfile,unittest
import nibabel as nib
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from rn_public.ucsd_batch_features import OFFSETS,FEATURES,symmetric_merged_glcm,sequence_features,prepare,process_case
from rn_public.ucsd_mri_intake import sha256


class BatchFeatureTests(unittest.TestCase):
    def test_hand_computed_checkerboard_merged_contrast(self):
        a=(np.indices((2,2,2)).sum(axis=0)%2+1).astype(np.uint8)
        roi=np.ones(a.shape,dtype=bool);p,e,d=sequence_features(a,roi,np.zeros_like(roi))
        self.assertEqual(len(OFFSETS),13)
        self.assertAlmostEqual(p['mean'],.5);self.assertAlmostEqual(p['std'],.5)
        self.assertAlmostEqual(p['entropy'],1)
        self.assertAlmostEqual(p['glcm_contrast'],961*16/28)
        self.assertEqual(d['neighbour_pairs_symmetric'],56);self.assertEqual(d['directions_with_pairs'],13)
        self.assertIsNone(e);self.assertEqual(d['erosion_error'],'empty_eroded_ROI')

    def test_axis_permutation_and_positive_intensity_transform_invariance(self):
        a=np.arange(1,126,dtype=float).reshape((5,5,5));roi=np.zeros(a.shape,dtype=bool);roi[1:4,1:4,1:4]=True
        x,_,_=sequence_features(a,roi,np.zeros_like(roi))
        y,_,_=sequence_features((a*3+7).transpose(2,0,1),roi.transpose(2,0,1),np.zeros_like(roi))
        for key in x:self.assertAlmostEqual(x[key],y[key],places=10)

    def test_GLCM_excludes_outside_ROI_and_does_not_invent_pairs(self):
        bins=np.full((3,3,3),99,dtype=int);roi=np.zeros(bins.shape,dtype=bool)
        roi[1,1,1]=True;bins[1,1,1]=1
        with self.assertRaisesRegex(ValueError,'no_valid'):symmetric_merged_glcm(bins,roi)
        roi[1,1,2]=True;bins[1,1,2]=32
        p,n,d=symmetric_merged_glcm(bins,roi)
        self.assertEqual((n,d),(2,1));self.assertEqual(p[0,31],.5);self.assertEqual(p[31,0],.5)

    def test_constant_primary_ROI_is_not_filled_with_zero_features(self):
        a=np.arange(1,28).reshape(3,3,3);r=np.zeros_like(a,dtype=bool);r[1,1,1]=True
        with self.assertRaisesRegex(ValueError,'constant_ROI'):sequence_features(a,r,np.zeros_like(r))

    def test_pinned_population_and_predictor_whitelist(self):
        c,t,m=prepare(ROOT)
        self.assertEqual((len(c),len(t),t.patient_id.nunique(),len(m)),(238,182,135,546))
        self.assertEqual(t.tumor_label.value_counts().to_dict(),{1:141,0:41})
        self.assertEqual(len(FEATURES),8)
        self.assertFalse(any(any(x in f.lower() for x in ['volume','label','roi','patient','adc']) for f in FEATURES))

    def test_failed_checkpoint_retries_after_same_input_file_is_restored(self):
        with tempfile.TemporaryDirectory(prefix='software_fixture_batch_') as temp:
            root=Path(temp);batch=root/'inputs';batch.mkdir();records=[]
            image=np.arange(1,9,dtype=np.uint8).reshape(2,2,2);mask=np.zeros_like(image);mask[0,0,:]=1
            for seq,data in [('FLAIR',image),('T1post',image+1),('BraTS_tumor_seg',mask)]:
                p=batch/(seq+'.nii.gz');img=nib.Nifti1Image(data,np.eye(4));img.set_sform(np.eye(4),1);nib.save(img,p)
                records.append(dict(ID='software_case',sequence=seq,mirror_filename=p.name,storage='batch_package',bytes=p.stat().st_size,sha256=sha256(p)))
            saved=(batch/'FLAIR.nii.gz').read_bytes();(batch/'FLAIR.nii.gz').unlink()
            a=process_case(root,batch,'software_case',records,'fixed_test_fingerprint')
            self.assertEqual(a['status'],'processing_failed');self.assertEqual(len(a['file_QC']),3)
            (batch/'FLAIR.nii.gz').write_bytes(saved)
            b=process_case(root,batch,'software_case',records,'fixed_test_fingerprint')
            self.assertEqual(b['status'],'complete');self.assertEqual(len(b['primary']),8)


if __name__=='__main__':unittest.main()
