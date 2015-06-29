# This module annotate the circRNA with gene names, and also filter the circRNA candidates by requiring "CircRNA could not from more than two annotated linear gene."
import pybedtools
import warnings
import logging
import os
import re
import HTSeq

class CircAnnotate(object):
    def __init__(self,strand=True):
        self.strand = strand
        
    def selectGeneGtf(self,gtf_file):
        # select gene features for gtf or gff annotation file
	gtf = HTSeq.GFF_Reader(gtf_file, end_included=True)
	new_gtf = open('_tmp_DCC/tmp_'+os.path.basename(gtf_file)+'.gene','w')
	for feature in gtf:
		# Select only exon line
		if feature.type == 'gene' or feature.type == 'exon':
			new_gtf.write(feature.get_gff_line())
		else:
			pass
	new_gtf.close()
    
    def annotate(self,circfile,annotationfile,output):
        # the circRNA file should be in a bed format, have chr\tstart\tend\t'.'\tjunctiontype\tstrand
        # The annotation file should be three column bed format
        
        # check the input
        with open(circfile,'r') as tmpcirc:
            tmpsplit = tmpcirc.readline().split('\t')
            if len(tmpsplit) != 6:
                warnings.warn('Input circRNA file is not the desired bed6 format!')
                logging.warning('Input circRNA file is not the desired bed6 format!')
            ncol = len(tmpsplit)
                
        #with open(annotationfile,'r') as tmpann:
        #    tmpsplit = tmpann.readline().split('\t')
        #    if len(tmpsplit) != 4:
        #        warnings.warn('Input annotation file is not the desired bed4 format!')
        #        logging.warning('Input annotation file is not the desired bed4 format!')
        
        ### Annotate gene names
        # Use bedtools to do annotation
        circ = pybedtools.BedTool(circfile)
        ann = pybedtools.BedTool(annotationfile)
        if self.strand:
            tmpintersect = circ.intersect(ann,wa=True,wb=True,loj=True,s=True,nonamecheck=True)
        else:
            tmpintersect = circ.intersect(ann,wa=True,wb=True,loj=True,s=False,nonamecheck=True)
        if self.strand:
            tmpresult = tmpintersect.groupby(g=(1,2,3,5,6),c=ncol+9,o='distinct')
        else:
            tmpresult = tmpintersect.groupby(g=(1,2,3,5),c=(ncol+7,ncol+9),o=('first','distinct'))
        tmpintersect.moveto('_tmp_DCC/tmp_intersect')
        tmpresult.moveto('_tmp_DCC/tmp_AnnotatedUnsorted')
        self.printbycolumns('_tmp_DCC/tmp_AnnotatedUnsorted',output,order=[1,2,3,6,4,5])
        #os.remove('_tmp_DCC/tmp_AnnotatedUnsorted')
          
    def annotateregions(self,circfile, annotationfile):
        # Annotate with regions (Exon, intron, intergenic)
        # create left and right circle bundary bedfiles: chr\tstart\tstart  chr\tend\tend
        tmp_left = open('_tmp_DCC/tmp_left','w')
        tmp_right = open('_tmp_DCC/tmp_right','w')
        circ = open(circfile,'r').readlines()
        for line in circ:
            line_split = line.split('\t')
            tmp_left.write('\t'.join((line_split[0],line_split[1],line_split[1],'.','.',line_split[5])))
            tmp_right.write('\t'.join((line_split[0],line_split[2].strip(),line_split[2].strip(),'.','.',line_split[5])))        
        tmp_left.close()
        tmp_right.close()
        
        # Bedtools annotate
        overall = pybedtools.BedTool(circfile)
        left = pybedtools.BedTool('_tmp_DCC/tmp_left')
        right = pybedtools.BedTool('_tmp_DCC/tmp_right')
        ann = pybedtools.BedTool(annotationfile)
        overallintersect = overall.intersect(ann,wa=True,wb=True,loj=True,s=False)
        leftintersect = left.intersect(ann,wa=True,wb=True,loj=True,s=False,nonamecheck=True)
        rightintersect = right.intersect(ann,wa=True,wb=True,loj=True,s=False,nonamecheck=True)
        overallresult = overallintersect.groupby(g=(1,2,3,6),c=9,o='distinct')
        leftresult = leftintersect.groupby(g=(1,2,3,6),c=9,o='distinct')
        rightresult = rightintersect.groupby(g=(1,2,3,6),c=9,o='distinct')
        
        # Convert BedTool format to dictionary
        overallresult = [str(i).split('\t') for i in overallresult]
        leftresult_dict = {}
        for line in leftresult:
            tmp = str(line).split('\t')
            leftresult_dict[(tmp[0],tmp[1],tmp[3])] = self.readRegionAnnotate(tmp[4].strip())
            
        rightresult_dict = {}
        for line in rightresult:
            tmp = str(line).split('\t')
            rightresult_dict[(tmp[0],tmp[1],tmp[3])] = self.readRegionAnnotate(tmp[4].strip())
        
        # Write result, due to duplicated start or end position, the three annotation list are in different length
        new_CircCoordinates = open('CircCoordinates','w')
        new_CircCoordinates.write('Chr\tStart\tEnd\tGene\tJunctionType\tStrand\tStart-End Region\tOverallRegion\n')
        for indx, line in enumerate(circ):
            tmp = line.split('\t')
            left_key = (tmp[0],tmp[1],tmp[5].strip())
            right_key = (tmp[0],tmp[2],tmp[5].strip())
            new_circline = line.strip()+'\t'+leftresult_dict[left_key]+'-'+rightresult_dict[right_key]+'\t'+overallresult[indx][4]
            new_CircCoordinates.write(new_circline)
        new_CircCoordinates.close()
    
    def readRegionAnnotate(self,annotatestring):
        if 'exon' in annotatestring:
            return 'exon'
        elif len(annotatestring) > 1 and annotatestring != 'region':
            return 'intron'
        elif len(annotatestring)==1 or annotatestring == 'region':
            return 'intergenic'
                    
    def filtbygene(self,circ2filter,output):
        # This funtion filter the circs base on: circRNAs should not come from two genes.
        out = open(output,'w')
        with open(circ2filter,'r') as circ:
	   for line in circ:
		tmp = line.split('\t')
		n=tmp[3].split(',')
		try:
		  if len(n)==1:
		      out.write(line)
		except IndexError:
			pass
	out.close()


    def printbycolumns(self,fileIn,fileOut,order=[],sep='\t',fillempty=True):
        tmpIn = open(fileIn,'r')
        tmpOut = open(fileOut,'w')
        for lines in tmpIn:
            tmpsplit = [x.strip() for x in lines.split(sep)]
            if fillempty:
                tmpsplit = ['.' if x=='' else x for x in tmpsplit]
            # Get gene_id or gene_name annotation
            tmpsplit[5] = self.searchGeneName(tmpsplit[5])                 
            tmpOut.write('\t'.join([tmpsplit[int(i)-1] for i in order])+'\n')
        tmpIn.close()
        tmpOut.close()
        
        
    def searchGeneName1(self,annotationstring):
        # Search for gene_name in gtf annotation, if gene_name cannot be found, look for gene_id
        # input example: gene_id "ENSG00000187634"; gene_name "SAMD11"; gene_source "ensembl_havana"; gene_biotype "lincRNA";
        ann = ','.join(list(set(re.findall(r'gene_name\=?\s?"([^;]*)"\;',annotationstring))))
        if len(ann)==0:
            # Look for "gene=", which is used in gff3 format
            ann = ','.join(list(set(re.findall(r'gene\=?\s?"([^;]*)"\;',annotationstring))))
            if len(ann)==0:
                # Look for gene_id
                ann = ','.join(list(set(re.findall(r'gene_id\=?\s?"([^;]*)"\;',annotationstring))))
                if len(ann)==0:
                    # Look for transcript_id
                    ann = ','.join(list(set(re.findall(r'transcript_id\=?\s?"([^;]*)"\;',annotationstring))))
        if len(ann)==0:
            ann = 'N/A'
        return ann
        
    def searchGeneName(self,annotationstring):
        if annotationstring == '.':
            genes = 'N/A'
        else:
            # Split the annotationstring by ',' which collapsed by bedtools groupby
            annotationstrings = annotationstring.split(',')
            collect = set()
            for annotation in annotationstrings:
                try:
                    attr = HTSeq.parse_GFF_attribute_string(annotation)
                    # Search for gene_name which is used by ensembl gtf annotation
                    try:
                        gene = attr['gene_name']
                    except KeyError:
                        # Search for gene, which might used in GFF annotation
                        try:
                            gene = attr['gene']
                        except KeyError:
                            # Search for gene_id
                            try:
                                gene = attr['gene_id']
                            except KeyError:
                                try:
                                    gene = attr['transcript_id']
                                except KeyError:
                                    gene = 'N/A'
                except:
                    gene = self.searchGeneName1(annotation)
                collect.add(gene)
            # Collapse all genes togethor
            if len(collect) > 1:
                try:
                    collect.remove('N/A')
                except KeyError:
                    pass
            genes = ','.join(collect)
            
        return genes
        
        
        