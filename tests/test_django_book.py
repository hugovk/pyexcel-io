from pyexcel_io import save_data, DB_DJANGO, OrderedDict, DEFAULT_SHEET_NAME
from pyexcel_io.djangobook import DjangoModelReader, DjangoModelWriter
from pyexcel_io.newbase import DjangoModelImporter, DjangoModelExporter
from pyexcel_io.newbase import DjangoModelImportAdapter, DjangoModelExportAdapter
from pyexcel_io.newbase import DjangoBookWriterNew, DjangoBookReaderNew

class Package:
    def __init__(self, raiseException=False, **keywords):
        self.keywords = keywords
        self.raiseException = raiseException

    def get_content(self):
        return self.keywords

    def save(self):
        if self.raiseException:
            raise Exception("test exception")
        else:
            pass


class Attributable:
    def __init__(self, adict):
        self.mydict = adict
        
    def __getattr__(self, field):
        return self.mydict[field]


class Objects:
    def __init__(self):
        self.objs = []
        
    def bulk_create(self, objs, batch_size):
        self.objs = [ o.get_content() for o in objs ]
        self.batch_size = batch_size

    def all(self):
        return [Attributable(o) for o in self.objs]


class Field:
    def __init__(self, name):
        self.attname = name


class Meta:
    instance = 1
    def __init__(self):
        self.model_name = "Sheet%d" % Meta.instance
        self.concrete_fields = []
        Meta.instance = Meta.instance + 1

    def update(self, data):
        for f in data:
            self.concrete_fields.append(Field(f))


class FakeDjangoModel:
    def __init__(self):
        self.objects = Objects()
        self._meta = Meta()

    def __call__(self, **keywords):
        return Package(**keywords)


class ExceptionObjects(Objects):
    def bulk_create(self, objs, batch_size):
        raise Exception("faked exception")


class FakeExceptionDjangoModel(FakeDjangoModel):
    def __init__(self, raiseException=False):
        self.objects = ExceptionObjects()
        self._meta = Meta()
        self.raiseException = raiseException

    def __call__(self, **keywords):
        return Package(raiseException=self.raiseException,
                       **keywords)


class TestException:
    def setUp(self):
        self.data  = [
            ["X", "Y", "Z"],
            [1, 2, 3],
            [4, 5, 6]
        ]
        self.result = [
            {'Y': 2, 'X': 1, 'Z': 3},
            {'Y': 5, 'X': 4, 'Z': 6}
        ]
        
    def test_sheet_save_to_django_model(self):
        model=FakeExceptionDjangoModel()
        writer = DjangoModelWriter([model, self.data[0], None, None])
        writer.write_array(self.data[1:])
        writer.close()
        # now raise excpetion
        model=FakeExceptionDjangoModel(raiseException=True)
        writer = DjangoModelWriter([model, self.data[0], None, None])
        writer.write_array(self.data[1:])
        writer.close()


class TestSheet:
    def setUp(self):
        self.data  = [
            ["X", "Y", "Z"],
            [1, 2, 3],
            [4, 5, 6]
        ]
        self.result = [
            {'Y': 2, 'X': 1, 'Z': 3},
            {'Y': 5, 'X': 4, 'Z': 6}
        ]
        
    def test_sheet_save_to_django_model(self):
        model=FakeDjangoModel()
        writer = DjangoModelWriter([model, self.data[0], None, None])
        writer.write_array(self.data[1:])
        writer.close()
        assert model.objects.objs == self.result

    def test_sheet_save_to_django_model_with_empty_array(self):
        model=FakeDjangoModel()
        data  = [
            ["X", "Y", "Z"],
            ['', '', ''],
            [1, 2, 3],
            [4, 5, 6]
        ]
        writer = DjangoModelWriter([model, data[0], None, None])
        writer.write_array(data[1:])
        writer.close()
        assert model.objects.objs == self.result

    def test_sheet_save_to_django_model_3(self):
        model=FakeDjangoModel()
        def wrapper(row):
            row[0] = row[0] + 1
            return row
        writer = DjangoModelWriter([model, self.data[0], None, wrapper])
        writer.write_array(self.data[1:])
        writer.close()
        assert model.objects.objs == [
            {'Y': 2, 'X': 2, 'Z': 3},
            {'Y': 5, 'X': 5, 'Z': 6}
        ]

    def test_sheet_save_to_django_model_skip_me(self):
        model=FakeDjangoModel()
        def wrapper(row):
            if row[0] == 4:
                return None
            else:
                return row
        writer = DjangoModelWriter([model, self.data[0], None, wrapper])
        writer.write_array(self.data[1:])
        writer.close()
        assert model.objects.objs == [
            {'Y': 2, 'X': 1, 'Z': 3}
        ]

    def test_load_sheet_from_django_model(self):
        model=FakeDjangoModel()
        importer = DjangoModelImporter()
        adapter = DjangoModelImportAdapter(model)
        adapter.set_column_names(self.data[0])
        importer.append(adapter)
        save_data(importer, {adapter.get_name(): self.data[1:]}, file_type=DB_DJANGO)
        assert model.objects.objs == self.result
        model._meta.update(["X", "Y", "Z"])
        reader = DjangoModelReader(model)
        data = reader.to_array()
        assert list(data) == self.data

    def test_mapping_array(self):
        data2 = [
            ["A", "B", "C"],
            [1, 2, 3],
            [4, 5, 6]
        ]
        mapdict = ["X", "Y", "Z"]
        model=FakeDjangoModel()
        writer = DjangoModelWriter([model, data2[0], mapdict, None])
        writer.write_array(data2[1:])
        writer.close()
        assert model.objects.objs == self.result

    def test_mapping_dict(self):
        data2 = [
            ["A", "B", "C"],
            [1, 2, 3],
            [4, 5, 6]
        ]
        mapdict = {
            "C": "Z",
            "A": "X",
            "B": "Y"
        }
        model=FakeDjangoModel()
        writer = DjangoModelWriter([model, data2[0], mapdict, None])
        writer.write_array(data2[1:])
        writer.close()
        assert model.objects.objs == self.result

    def test_empty_model(self):
        model = FakeDjangoModel()
        reader = DjangoModelReader(model)
        data = reader.to_array()
        assert data == []


class TestMultipleModels:
    def setUp(self):
        self.content = OrderedDict()
        self.content.update({"Sheet1": [[u'X', u'Y', u'Z'], [1, 4, 7], [2, 5, 8], [3, 6, 9]]})
        self.content.update({"Sheet2": [[u'A', u'B', u'C'], [1, 4, 7], [2, 5, 8], [3, 6, 9]]})
        self.result1 = [{'Y': 4, 'X': 1, 'Z': 7}, {'Y': 5, 'X': 2, 'Z': 8}, {'Y': 6, 'X': 3, 'Z': 9}]
        self.result2 = [{'B': 4, 'A': 1, 'C': 7}, {'B': 5, 'A': 2, 'C': 8}, {'B': 6, 'A': 3, 'C': 9}]

    def test_save_to_more_models(self):
        model1=FakeDjangoModel()
        model2=FakeDjangoModel()
        importer = DjangoModelImporter()
        adapter1 = DjangoModelImportAdapter(model1)
        adapter1.set_column_names(self.content['Sheet1'][0])
        adapter2 = DjangoModelImportAdapter(model2)
        adapter2.set_column_names(self.content['Sheet2'][0])
        importer.append(adapter1)
        importer.append(adapter2)
        to_store = {
            adapter1.get_name(): self.content['Sheet1'][1:],
            adapter2.get_name(): self.content['Sheet2'][1:]
        }
        writer = DjangoBookWriterNew()
        writer.open_content(importer)
        writer.write(to_store)
        writer.close()
        assert model1.objects.objs == self.result1
        assert model2.objects.objs == self.result2

    def test_reading_from_more_models(self):
        model1=FakeDjangoModel()
        model2=FakeDjangoModel()
        importer = DjangoModelImporter()
        adapter1 = DjangoModelImportAdapter(model1)
        adapter1.set_column_names(self.content['Sheet1'][0])
        adapter2 = DjangoModelImportAdapter(model2)
        adapter2.set_column_names(self.content['Sheet2'][0])
        importer.append(adapter1)
        importer.append(adapter2)
        to_store = {
           adapter1.get_name(): self.content['Sheet1'][1:],
           adapter2.get_name(): self.content['Sheet2'][1:]
        }
        save_data(importer, to_store, file_type=DB_DJANGO)
        assert model1.objects.objs == self.result1
        assert model2.objects.objs == self.result2
        model1._meta.model_name = "Sheet1"
        model2._meta.model_name = "Sheet2"
        model1._meta.update(["X", "Y", "Z"])
        model2._meta.update(["A", "B", "C"])
        exporter = DjangoModelExporter()
        adapter1 = DjangoModelExportAdapter(model1)
        adapter2 = DjangoModelExportAdapter(model2)
        exporter.append(adapter1)
        exporter.append(adapter2)
        reader = DjangoBookReaderNew()
        reader.open_content(exporter)
        data = reader.read_all()
        for key in data.keys():
            data[key] = list(data[key])
        assert data == self.content

    def test_special_case_where_only_one_model_used(self):
        model1=FakeDjangoModel()
        importer = DjangoModelImporter()
        adapter = DjangoModelImportAdapter(model1)
        adapter.set_column_names(self.content['Sheet1'][0])
        importer.append(adapter)
        to_store = {
            adapter.get_name(): self.content['Sheet1'][1:],
            "Sheet2": self.content['Sheet2'][1:]
        }
        save_data(importer, to_store, file_type=DB_DJANGO)
        assert model1.objects.objs == self.result1
        model1._meta.model_name = "Sheet1"
        model1._meta.update(["X", "Y", "Z"])
        exporter = DjangoModelExporter()
        adapter = DjangoModelExportAdapter(model1)
        exporter.append(adapter)
        reader = DjangoBookReaderNew()
        reader.open_content(exporter)
        data = reader.read_all()
        assert list(data['Sheet1']) == self.content['Sheet1']
