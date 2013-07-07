from django import forms
from django.shortcuts import render

from nspdice_probability.die import Die
from nspdice_probability.formmanager import manager_factory

import re
import string

class ModeForm(forms.Form):
  MODE_CHOICES = (
    ('target','Target'),
    ('vs','Versus'),
  )

  mode =  forms.ChoiceField(choices=MODE_CHOICES,required=False)

class ColumnForm(forms.Form):

  SKILL_CHOICES = (
    ('del','Delete'),
    ('pro','Property'),
    ('Skill', (
      ('1','LvL 1 (D6)'),
      ('2','LvL 2 (D8)'),
      ('3','LvL 3 (D10)'),
      ('4','LvL 4 (D12)'),
      ('5','LvL 5 (D20)'),
      ('6','LvL 6 (+6)'),
    )),
  )
  
  PRO_CHOICES = (
    ('1','1-8   (D6)'),
    ('2','9-14  (D8)'),
    ('3','15-17 (D10)'),
    ('4','18-9  (D12)'),
    ('5','20    (D20)'),
    ('6','21-24 (D16)'),
    ('7','25-29 (D24)'),
    ('8','30    (D30)'),
  )

  def _flatten(self,choices):
    flat = []
    for choice, value in choices:
      if isinstance(value, (list, tuple)):
        flat.extend(value)
      else:
        flat.append((choice,value))
    return flat

  def get_skill_display(self):
    value = self.cleaned_data['skill']
    return dict(self._flatten(self.SKILL_CHOICES)).get(value, value)

  def get_pro_display(self):
    value = self.cleaned_data['pro']
    return dict(self._flatten(self.PRO_CHOICES)).get(value, value)

  skill = forms.ChoiceField(choices=SKILL_CHOICES)
  pro =   forms.ChoiceField(choices=PRO_CHOICES)

  def keep(self):
    if not self.is_valid():
      return True
    else:
      return self.cleaned_data['skill'] != 'del'

  def details(self):
    return "%s\n%s"%(self.get_skill_display(),self.get_pro_display())

class CustomDieForm(forms.Form):
  die = forms.CharField(required=False)

  num = None

  _re_const = re.compile('^(\d+)$')
  _re_single = re.compile('^d(\d+)$')
  _re_multi = re.compile('^(\d+)d(\d+)$')

  def get_skill_display(self):
    return "Custom"

  def get_pro_display(self):
    return self.num

  def clean_die(self):
    raw = self.cleaned_data['die']
    self.rawdice = raw.split()
    if len(self.rawdice)==0:
      return None

    # Place-holder die that always rolls a sum of 0
    die = Die.const(0)

    # For each proposed die
    for rd in self.rawdice:
      # Check for constants
      m = self._re_const.match(rd)
      if m:
        die += Die.const(int(m.group(1)))
        
        continue
      
      # Check for single die
      m = self._re_single.match(rd)
      if m:
        die += Die(int(m.group(1)))
        continue
      
      # Check for multiple copies of same die
      m = self._re_multi.match(rd)
      if m:
        die += Die(int(m.group(2))).duplicate(int(m.group(1)))
        continue

      # None of the above matched; the die is invalid.
      raise forms.ValidationError("Invalid die: %s"%rd)
      
    return die

  def keep(self):
    if not self.is_valid():
      return True
    else:
      return self.cleaned_data['die'] != None

  def details(self):
    return string.join(self.rawdice)


def probability_reference(request):
  ColumnFormManager = manager_factory(ColumnForm)
  CustomDieFormManager = manager_factory(CustomDieForm)

  mode = 'target'
  if "mode" in request.GET:
    modeform = ModeForm(request.GET)
    if modeform.is_valid():
      mode = modeform.cleaned_data.get('mode','target')
  else:
    modeform = ModeForm()

  columnmanager = ColumnFormManager(request.GET)
  customdiemanager = CustomDieFormManager(request.GET)

  for i, f in enumerate(customdiemanager.base_forms(),1):
    f.num = i

  if columnmanager.is_valid() and customdiemanager.is_valid():
    # Create the corresponding die for each form.
    dice = [
      build_die(d['skill'],d['pro'])
      for d in columnmanager.cleaned_data()
    ]
    dice += [ d['die'] for d in customdiemanager.cleaned_data() ]
  else:
    dice = []

  if mode == 'target':
    # Compute probability for each die.
    result = transpose([ d.probability_reach() for d in dice ])

    return render(request, 'target.html', {
      'modeform': modeform,
      'columnmanager': columnmanager,
      'customdiemanager': customdiemanager,
      'result': result,
    })

  elif mode == 'vs':
    result = [ [ a.probability_vs(b) for a in dice ] for b in dice ]

    return render(request, 'versus.html', {
      'modeform': modeform,
      'columnmanager': columnmanager,
      'customdiemanager': customdiemanager,
      'result': result,
    })
  else:
    return render(request, 'probability_reference.html', {
      'modeform': modeform,
      'columnmanager': columnmanager,
      'customdiemanager': customdiemanager,
    })

SKILL_DIE = {}
SKILL_DIE['1'] = Die(4) + Die(6)
SKILL_DIE['2'] = SKILL_DIE['1'] + Die(8)
SKILL_DIE['3'] = SKILL_DIE['2'] + Die(10)
SKILL_DIE['4'] = SKILL_DIE['3'] + Die(12)
SKILL_DIE['5'] = SKILL_DIE['4'] + Die(20)
SKILL_DIE['6'] = SKILL_DIE['5'] + Die.const(6)

DB_DIE = {}
DB_DIE['1'] = Die(6)
DB_DIE['2'] = Die(8)
DB_DIE['3'] = Die(10)
DB_DIE['4'] = Die(12)
DB_DIE['5'] = Die(20)
DB_DIE['6'] = Die(16)
DB_DIE['7'] = Die(24)
DB_DIE['8'] = Die(30)

PRO_DIE = {}
PRO_DIE['1'] = Die(4) +       DB_DIE['1']
PRO_DIE['2'] = PRO_DIE['1'] + DB_DIE['2']
PRO_DIE['3'] = PRO_DIE['2'] + DB_DIE['3']
PRO_DIE['4'] = PRO_DIE['3'] + DB_DIE['4']
PRO_DIE['5'] = PRO_DIE['4'] + DB_DIE['5']
PRO_DIE['6'] = PRO_DIE['5'] + DB_DIE['6']
PRO_DIE['7'] = PRO_DIE['5'] + DB_DIE['7']
PRO_DIE['8'] = PRO_DIE['5'] + DB_DIE['8']

def build_die(skill,pro):
  if skill == 'pro':
    return PRO_DIE[pro]
  else:
    return SKILL_DIE[skill] + DB_DIE[pro]

def transpose(data):
  if len(data)==0:
    return []
  if len(data)==1:
    return map(lambda x: [x],*data)
  else:
    return map(None,*data)